/**
 * Aerix (arx) — Ultra-Fast Native Dispatcher & Cache Accelerator
 * Standard: ANSI C99 / Windows API
 * Compiled with: gcc -O2 -s -o dist/arx.exe src/native/arx_runner.c
 *
 * Provides sub-millisecond execution for cached .arx binaries and
 * orchestrates the compiler pipeline with minimum latency.
 */

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// 64-bit FNV-1a fast hash
static uint64_t fnv1a_hash(const unsigned char* data, size_t len) {
    uint64_t hash = 14695981039346656037ULL;
    for (size_t i = 0; i < len; i++) {
        hash ^= (uint64_t)data[i];
        hash *= 1099511628211ULL;
    }
    return hash;
}

static int run_process(const char* cmdline) {
    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    char cmd_copy[8192];
    strncpy(cmd_copy, cmdline, sizeof(cmd_copy) - 1);
    cmd_copy[sizeof(cmd_copy) - 1] = '\0';

    if (!CreateProcessA(NULL, cmd_copy, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {
        return -1;
    }

    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD exit_code = 0;
    GetExitCodeProcess(pi.hProcess, &exit_code);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return (int)exit_code;
}

int main(int argc, char** argv) {
    const char* target_file = NULL;
    int arg_start = 2;

    if (argc == 2 && argv[1][0] != '-') {
        target_file = argv[1];
        arg_start = 2;
    } else if (argc >= 3 && strcmp(argv[1], "run") == 0 && argv[2][0] != '-') {
        target_file = argv[2];
        arg_start = 3;
    }

    // ----------------------------------------------------
    // Fast Path: Check Content-Hashed Binary Cache
    // ----------------------------------------------------
    if (target_file) {
        FILE* f = fopen(target_file, "rb");
        if (f) {
            fseek(f, 0, SEEK_END);
            long sz = ftell(f);
            fseek(f, 0, SEEK_SET);

            if (sz >= 0) {
                unsigned char* buf = (unsigned char*)malloc(sz + 1);
                if (buf) {
                    if (fread(buf, 1, sz, f) == (size_t)sz) {
                        uint64_t h = fnv1a_hash(buf, sz);
                        free(buf);
                        fclose(f);
                        f = NULL;

                        char temp_path[MAX_PATH];
                        GetTempPathA(MAX_PATH, temp_path);

                        char cached_exe[MAX_PATH];
                        snprintf(cached_exe, sizeof(cached_exe), "%saerix_cache\\fast_%llx.exe", temp_path, (unsigned long long)h);

                        DWORD attr = GetFileAttributesA(cached_exe);
                        if (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY)) {
                            // CACHE HIT! Instant execution in < 15ms!
                            char cmdline[4096];
                            int written = snprintf(cmdline, sizeof(cmdline), "\"%s\"", cached_exe);
                            for (int i = arg_start; i < argc; i++) {
                                written += snprintf(cmdline + written, sizeof(cmdline) - written, " \"%s\"", argv[i]);
                            }
                            return run_process(cmdline);
                        }
                    } else {
                        free(buf);
                    }
                }
            }
            if (f) fclose(f);
        }
    }

    // ----------------------------------------------------
    // Slow / Compile Path: Forward to Aerix Compiler Engine
    // ----------------------------------------------------
    // 1. Check if python is available and points to aerix repo
    char exe_dir[MAX_PATH];
    GetModuleFileNameA(NULL, exe_dir, MAX_PATH);
    char* last_slash = strrchr(exe_dir, '\\');
    if (last_slash) *last_slash = '\0';

    char compiler_cmd[8192];
    compiler_cmd[0] = '\0';

    // Check for repo arx.py
    char repo_script[] = "Z:\\VSCode\\AerixLang\\src\\arx.py";
    DWORD repo_attr = GetFileAttributesA(repo_script);
    if (repo_attr != INVALID_FILE_ATTRIBUTES) {
        snprintf(compiler_cmd, sizeof(compiler_cmd), "python \"%s\"", repo_script);
    } else {
        // Fallback to standalone core
        char core_exe[MAX_PATH];
        snprintf(core_exe, sizeof(core_exe), "%s\\arx_core.exe", exe_dir);
        snprintf(compiler_cmd, sizeof(compiler_cmd), "\"%s\"", core_exe);
    }

    // Append original arguments
    int cur_len = (int)strlen(compiler_cmd);
    for (int i = 1; i < argc; i++) {
        cur_len += snprintf(compiler_cmd + cur_len, sizeof(compiler_cmd) - cur_len, " \"%s\"", argv[i]);
    }

    return run_process(compiler_cmd);
}


