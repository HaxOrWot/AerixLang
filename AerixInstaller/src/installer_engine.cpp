#include "installer_engine.hpp"
#include "resource.h"

#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#include <zlib.h>

#include <cstdint>
#include <cstring>
#include <cwctype>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <vector>

namespace fs = std::filesystem;

namespace {

std::wstring Utf8ToWide(const std::string& utf8) {
    if (utf8.empty()) return L"";
    int needed = MultiByteToWideChar(CP_UTF8, 0, utf8.data(), static_cast<int>(utf8.size()), nullptr, 0);
    if (needed <= 0) return L"";
    std::wstring out(static_cast<size_t>(needed), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, utf8.data(), static_cast<int>(utf8.size()), out.data(), needed);
    return out;
}

std::wstring ExpandEnv(const wchar_t* expr) {
    DWORD needed = ExpandEnvironmentStringsW(expr, nullptr, 0);
    if (needed == 0) return L"";
    std::wstring out(needed, L'\0');
    ExpandEnvironmentStringsW(expr, out.data(), needed);
    if (!out.empty() && out.back() == L'\0') out.pop_back();
    return out;
}

std::wstring ToLower(std::wstring s) {
    for (wchar_t& c : s) c = static_cast<wchar_t>(towlower(c));
    return s;
}

std::wstring TrimTrailingSlashes(std::wstring s) {
    while (s.size() > 3 && (s.back() == L'\\' || s.back() == L'/')) {
        s.pop_back();
    }
    return s;
}

bool LoadRcData(HMODULE mod, int res_id, const uint8_t*& ptr, size_t& size) {
    HRSRC hrsrc = FindResourceW(mod, MAKEINTRESOURCEW(res_id), MAKEINTRESOURCEW(10));  // RT_RCDATA
    if (!hrsrc) return false;
    HGLOBAL hglob = LoadResource(mod, hrsrc);
    if (!hglob) return false;
    DWORD sz = SizeofResource(mod, hrsrc);
    void* locked = LockResource(hglob);
    if (!locked) return false;
    ptr = static_cast<const uint8_t*>(locked);
    size = static_cast<size_t>(sz);
    return true;
}

std::wstring FindOnPathOrCandidates(const std::vector<std::wstring>& names,
                                    const std::vector<std::wstring>& candidates) {
    for (const auto& name : names) {
        wchar_t buf[MAX_PATH] = {};
        if (SearchPathW(nullptr, name.c_str(), nullptr, MAX_PATH, buf, nullptr) > 0) {
            return buf;
        }
    }
    for (const auto& c : candidates) {
        std::error_code ec;
        if (!c.empty() && fs::exists(fs::path(c), ec)) {
            return c;
        }
    }
    return L"";
}

bool RegSetStr(HKEY root, const std::wstring& subkey, const wchar_t* name,
               const std::wstring& value, DWORD type = REG_SZ) {
    HKEY hkey = nullptr;
    LONG rc = RegCreateKeyExW(root, subkey.c_str(), 0, nullptr, 0, KEY_SET_VALUE | KEY_QUERY_VALUE, nullptr, &hkey, nullptr);
    if (rc != ERROR_SUCCESS) return false;
    DWORD bytes = static_cast<DWORD>((value.size() + 1) * sizeof(wchar_t));
    rc = RegSetValueExW(hkey, name, 0, type, reinterpret_cast<const BYTE*>(value.c_str()), bytes);
    RegCloseKey(hkey);
    return rc == ERROR_SUCCESS;
}

bool RegSetDword(HKEY root, const std::wstring& subkey, const wchar_t* name, DWORD value) {
    HKEY hkey = nullptr;
    LONG rc = RegCreateKeyExW(root, subkey.c_str(), 0, nullptr, 0, KEY_SET_VALUE, nullptr, &hkey, nullptr);
    if (rc != ERROR_SUCCESS) return false;
    rc = RegSetValueExW(hkey, name, 0, REG_DWORD, reinterpret_cast<const BYTE*>(&value), sizeof(value));
    RegCloseKey(hkey);
    return rc == ERROR_SUCCESS;
}

std::wstring RegGetStr(HKEY root, const std::wstring& subkey, const wchar_t* name, DWORD* out_type = nullptr) {
    HKEY hkey = nullptr;
    if (RegOpenKeyExW(root, subkey.c_str(), 0, KEY_QUERY_VALUE, &hkey) != ERROR_SUCCESS) return L"";
    DWORD type = 0;
    DWORD bytes = 0;
    LONG rc = RegQueryValueExW(hkey, name, nullptr, &type, nullptr, &bytes);
    if (rc != ERROR_SUCCESS || bytes < sizeof(wchar_t)) {
        RegCloseKey(hkey);
        return L"";
    }
    std::wstring buf(bytes / sizeof(wchar_t), L'\0');
    rc = RegQueryValueExW(hkey, name, nullptr, &type, reinterpret_cast<BYTE*>(buf.data()), &bytes);
    RegCloseKey(hkey);
    if (rc != ERROR_SUCCESS) return L"";
    while (!buf.empty() && buf.back() == L'\0') buf.pop_back();
    if (out_type) *out_type = type;
    return buf;
}

void RegDelValue(HKEY root, const std::wstring& subkey, const wchar_t* name) {
    HKEY hkey = nullptr;
    if (RegOpenKeyExW(root, subkey.c_str(), 0, KEY_SET_VALUE, &hkey) == ERROR_SUCCESS) {
        RegDeleteValueW(hkey, name);
        RegCloseKey(hkey);
    }
}

void BroadcastEnvChange() {
    SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0,
                        reinterpret_cast<LPARAM>(L"Environment"),
                        SMTO_ABORTIFHUNG, 3000, nullptr);
}

std::vector<std::wstring> SplitPathList(const std::wstring& raw) {
    std::vector<std::wstring> parts;
    std::wstringstream ss(raw);
    std::wstring item;
    while (std::getline(ss, item, L';')) {
        while (!item.empty() && (item.front() == L' ' || item.front() == L'\t')) item.erase(item.begin());
        while (!item.empty() && (item.back() == L' ' || item.back() == L'\t')) item.pop_back();
        if (!item.empty()) parts.push_back(item);
    }
    return parts;
}

std::wstring JoinPathList(const std::vector<std::wstring>& parts) {
    std::wstring out;
    for (size_t i = 0; i < parts.size(); ++i) {
        if (i > 0) out += L';';
        out += parts[i];
    }
    return out;
}

bool AddUserPathEntry(const std::wstring& bin_dir) {
    DWORD type = REG_EXPAND_SZ;
    std::wstring current = RegGetStr(HKEY_CURRENT_USER, L"Environment", L"Path", &type);
    auto entries = SplitPathList(current);
    std::wstring target_norm = ToLower(TrimTrailingSlashes(bin_dir));
    for (const auto& e : entries) {
        if (ToLower(TrimTrailingSlashes(e)) == target_norm) {
            return true;
        }
    }
    entries.push_back(bin_dir);
    return RegSetStr(HKEY_CURRENT_USER, L"Environment", L"Path", JoinPathList(entries),
                     type == REG_SZ ? REG_EXPAND_SZ : type);
}

void RemoveUserPathEntry(const std::wstring& bin_dir) {
    DWORD type = REG_EXPAND_SZ;
    std::wstring current = RegGetStr(HKEY_CURRENT_USER, L"Environment", L"Path", &type);
    if (current.empty()) return;
    auto entries = SplitPathList(current);
    std::wstring target_norm = ToLower(TrimTrailingSlashes(bin_dir));
    std::vector<std::wstring> kept;
    for (const auto& e : entries) {
        if (ToLower(TrimTrailingSlashes(e)) != target_norm) {
            kept.push_back(e);
        }
    }
    RegSetStr(HKEY_CURRENT_USER, L"Environment", L"Path", JoinPathList(kept), type);
}

bool RunHiddenProcess(const std::wstring& cmdline, DWORD timeout_ms = 60000) {
    STARTUPINFOW si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi{};
    std::wstring mutable_cmd = cmdline;
    if (!CreateProcessW(nullptr, mutable_cmd.data(), nullptr, nullptr, FALSE,
                        CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi)) {
        return false;
    }
    DWORD wait_rc = WaitForSingleObject(pi.hProcess, timeout_ms);
    DWORD exit_code = 1;
    if (wait_rc == WAIT_OBJECT_0) {
        GetExitCodeProcess(pi.hProcess, &exit_code);
    } else {
        TerminateProcess(pi.hProcess, 1);
    }
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return exit_code == 0;
}

bool ExtractPayload(HMODULE mod,
                    const fs::path& dest_root,
                    const ProgressCallback& progress,
                    std::wstring& error_out) {
    const uint8_t* res_ptr = nullptr;
    size_t res_size = 0;
    if (!LoadRcData(mod, IDR_PAYLOAD, res_ptr, res_size) || res_size < 20) {
        error_out = L"Embedded installation payload resource (IDR_PAYLOAD) could not be loaded.";
        return false;
    }

    if (std::memcmp(res_ptr, "ARXP", 4) != 0) {
        error_out = L"Invalid embedded payload header (expected ARXP).";
        return false;
    }

    uint32_t fmt_ver = 0;
    uint32_t file_count = 0;
    uint64_t raw_size = 0;
    std::memcpy(&fmt_ver, res_ptr + 4, 4);
    std::memcpy(&file_count, res_ptr + 8, 4);
    std::memcpy(&raw_size, res_ptr + 12, 8);
    if (fmt_ver != 1 || raw_size > (256ULL * 1024ULL * 1024ULL)) {
        error_out = L"Unsupported embedded payload version or size.";
        return false;
    }

    std::vector<uint8_t> raw(static_cast<size_t>(raw_size));
    uLongf dest_len = static_cast<uLongf>(raw_size);
    int zrc = uncompress(raw.data(), &dest_len, res_ptr + 20, static_cast<uLong>(res_size - 20));
    if (zrc != Z_OK || dest_len != raw_size) {
        error_out = L"Failed to decompress embedded payload.";
        return false;
    }

    size_t offset = 0;
    for (uint32_t i = 0; i < file_count; ++i) {
        if (offset + 4 > raw.size()) {
            error_out = L"Corrupted payload entry path length.";
            return false;
        }
        uint32_t path_len = 0;
        std::memcpy(&path_len, raw.data() + offset, 4);
        offset += 4;
        if (offset + path_len + 8 > raw.size()) {
            error_out = L"Corrupted payload entry metadata.";
            return false;
        }
        std::string rel_utf8(reinterpret_cast<const char*>(raw.data() + offset), path_len);
        offset += path_len;

        uint64_t data_len = 0;
        std::memcpy(&data_len, raw.data() + offset, 8);
        offset += 8;
        if (offset + data_len > raw.size()) {
            error_out = L"Corrupted payload file stream.";
            return false;
        }

        fs::path target = dest_root / fs::path(Utf8ToWide(rel_utf8));
        std::error_code ec;
        fs::create_directories(target.parent_path(), ec);
        if (ec) {
            error_out = L"Unable to create directory: " + target.parent_path().wstring();
            return false;
        }

        std::ofstream out(target, std::ios::binary | std::ios::trunc);
        if (!out) {
            error_out = L"Unable to write file: " + target.wstring();
            return false;
        }
        if (data_len > 0) {
            out.write(reinterpret_cast<const char*>(raw.data() + offset), static_cast<std::streamsize>(data_len));
        }
        out.close();
        if (!out) {
            error_out = L"Disk write failure for: " + target.wstring();
            return false;
        }
        offset += static_cast<size_t>(data_len);

        if (progress) {
            int pct = 8 + static_cast<int>((58ULL * (i + 1)) / (file_count > 0 ? file_count : 1));
            progress(pct, L"Extracting: " + Utf8ToWide(rel_utf8));
        }
    }
    return true;
}

void InstallExtensionToEditor(const std::wstring& editor_name,
                              const std::wstring& cli_path,
                              const fs::path& vsix_path,
                              const fs::path& unpacked_src,
                              const fs::path& fallback_dir,
                              const ProgressCallback& progress,
                              int pct) {
    bool cli_ok = false;
    if (!cli_path.empty() && fs::exists(vsix_path)) {
        if (progress) progress(pct - 2, L"Installing " + editor_name + L" extension via CLI...");
        std::wstring cmd = L"cmd.exe /C \"\"" + cli_path + L"\" --install-extension \"" + vsix_path.wstring() + L"\" --force\"";
        cli_ok = RunHiddenProcess(cmd, 45000);
    }

    if (!cli_ok && fs::exists(unpacked_src)) {
        if (progress) progress(pct, L"Deploying " + editor_name + L" extension files directly...");
        std::error_code ec;
        fs::remove_all(fallback_dir, ec);
        fs::create_directories(fallback_dir, ec);
        fs::copy(unpacked_src, fallback_dir, fs::copy_options::recursive | fs::copy_options::overwrite_existing, ec);
    } else if (progress) {
        progress(pct, editor_name + L" extension installed.");
    }
}

}  // namespace

std::wstring GetDefaultInstallDir() {
    std::wstring local = ExpandEnv(L"%LOCALAPPDATA%");
    if (local.empty()) return L"C:\\Aerix";
    return (fs::path(local) / L"Programs" / L"Aerix").wstring();
}

std::wstring GetLicenseText(void* hInstance) {
    const uint8_t* ptr = nullptr;
    size_t sz = 0;
    if (!LoadRcData(static_cast<HMODULE>(hInstance), IDR_LICENSE, ptr, sz)) {
        return L"MIT License\r\n\r\nCopyright (c) AerixLang";
    }
    std::string raw(reinterpret_cast<const char*>(ptr), sz);
    std::string normalized;
    normalized.reserve(raw.size() + 32);
    for (size_t i = 0; i < raw.size(); ++i) {
        if (raw[i] == '\n' && (i == 0 || raw[i - 1] != '\r')) {
            normalized.push_back('\r');
        }
        normalized.push_back(raw[i]);
    }
    return Utf8ToWide(normalized);
}

std::wstring DetectVSCodeCli() {
    std::wstring local = ExpandEnv(L"%LOCALAPPDATA%");
    std::wstring pf = ExpandEnv(L"%ProgramFiles%");
    std::wstring pfx86 = ExpandEnv(L"%ProgramFiles(x86)%");
    return FindOnPathOrCandidates(
        {L"code.cmd", L"code"},
        {
            local + L"\\Programs\\Microsoft VS Code\\bin\\code.cmd",
            pf + L"\\Microsoft VS Code\\bin\\code.cmd",
            pfx86 + L"\\Microsoft VS Code\\bin\\code.cmd",
        });
}

std::wstring DetectAntigravityCli() {
    std::wstring local = ExpandEnv(L"%LOCALAPPDATA%");
    std::wstring pf = ExpandEnv(L"%ProgramFiles%");
    return FindOnPathOrCandidates(
        {L"antigravity.cmd", L"antigravity-ide.cmd", L"antigravity"},
        {
            local + L"\\Programs\\Antigravity\\bin\\antigravity.cmd",
            local + L"\\Programs\\Antigravity IDE\\bin\\antigravity-ide.cmd",
            pf + L"\\Antigravity IDE\\bin\\antigravity-ide.cmd",
        });
}

bool RunInstall(void* hInstance,
                const InstallOptions& opts,
                const ProgressCallback& progress,
                std::wstring& error_out) {
    if (opts.install_dir.empty()) {
        error_out = L"Destination folder cannot be empty.";
        return false;
    }

    fs::path root = TrimTrailingSlashes(opts.install_dir);
    std::error_code ec;
    fs::create_directories(root, ec);
    if (ec) {
        error_out = L"Cannot create destination folder: " + root.wstring();
        return false;
    }

    if (progress) progress(5, L"Preparing destination: " + root.wstring());
    if (!ExtractPayload(static_cast<HMODULE>(hInstance), root, progress, error_out)) {
        return false;
    }

    if (progress) progress(70, L"Creating uninstaller...");
    wchar_t self_path[MAX_PATH] = {};
    if (GetModuleFileNameW(nullptr, self_path, MAX_PATH) > 0) {
        fs::path uninst_path = root / L"Uninstall.exe";
        if (ToLower(fs::path(self_path).wstring()) != ToLower(uninst_path.wstring())) {
            fs::copy_file(self_path, uninst_path, fs::copy_options::overwrite_existing, ec);
        }
    }

    if (opts.configure_env) {
        if (progress) progress(76, L"Configuring AERIX_* environment variables & User PATH...");
        std::wstring stdlib_dir = (root / L"stdlib").wstring();
        std::wstring modules_dir = (root / L"modules").wstring();
        std::wstring bin_dir = (root / L"bin").wstring();
        RegSetStr(HKEY_CURRENT_USER, L"Environment", L"AERIX_HOME", root.wstring());
        RegSetStr(HKEY_CURRENT_USER, L"Environment", L"AERIX_STDLIB", stdlib_dir);
        RegSetStr(HKEY_CURRENT_USER, L"Environment", L"AERIX_STDLIB_PATH", stdlib_dir);
        RegSetStr(HKEY_CURRENT_USER, L"Environment", L"AERIX_MODULE_PATH", modules_dir);
        AddUserPathEntry(bin_dir);
        SetEnvironmentVariableW(L"AERIX_HOME", root.c_str());
        SetEnvironmentVariableW(L"AERIX_STDLIB", stdlib_dir.c_str());
        SetEnvironmentVariableW(L"AERIX_STDLIB_PATH", stdlib_dir.c_str());
        SetEnvironmentVariableW(L"AERIX_MODULE_PATH", modules_dir.c_str());
        BroadcastEnvChange();
    }

    if (opts.file_associations) {
        if (progress) progress(82, L"Registering .arx file associations and Explorer icons...");
        std::wstring file_ico = (root / L"assets" / L"aerix_file.ico").wstring();
        std::wstring app_ico = (root / L"assets" / L"aerix.ico").wstring();
        std::wstring arx_exe = (root / L"bin" / L"arx.exe").wstring();

        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\.arx", nullptr, L"Aerix.SourceFile");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\.arx", L"Content Type", L"text/plain");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\.arx", L"PerceivedType", L"text");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\.arx\\OpenWithProgids", L"Aerix.SourceFile", L"");

        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile", nullptr, L"Aerix Source Code");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile", L"FriendlyTypeName", L"Aerix Source Code");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile\\DefaultIcon", nullptr, file_ico + L",0");

        std::wstring vscode = DetectVSCodeCli();
        std::wstring agy = DetectAntigravityCli();
        std::wstring editor_cmd = !agy.empty() ? agy : (!vscode.empty() ? vscode : L"notepad.exe");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile\\shell\\open", nullptr, L"Open with Code Editor");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile\\shell\\open\\command", nullptr,
                  L"\"" + editor_cmd + L"\" \"%1\"");

        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile\\shell\\run", nullptr, L"Run with Aerix (arx run)");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile\\shell\\run", L"Icon", app_ico + L",0");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile\\shell\\run\\command", nullptr,
                  L"cmd.exe /K \"\"" + arx_exe + L"\" run \"%1\"\"");

        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile\\shell\\build", nullptr, L"Build Executable (arx build)");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile\\shell\\build", L"Icon", app_ico + L",0");
        RegSetStr(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile\\shell\\build\\command", nullptr,
                  L"cmd.exe /K \"\"" + arx_exe + L"\" build \"%1\"\"");

        SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, nullptr, nullptr);
    }

    if (progress) progress(87, L"Registering Windows Apps & Features entry...");
    const std::wstring uninst_key = L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AerixLang";
    std::wstring uninst_exe = (root / L"Uninstall.exe").wstring();
    RegSetStr(HKEY_CURRENT_USER, uninst_key, L"DisplayName",
              std::wstring(L"Aerix ") + AERIX_VERSION_WSTR);
    RegSetStr(HKEY_CURRENT_USER, uninst_key, L"DisplayVersion", AERIX_VERSION_WSTR);
    RegSetStr(HKEY_CURRENT_USER, uninst_key, L"Publisher", L"HaxOrWot");
    RegSetStr(HKEY_CURRENT_USER, uninst_key, L"URLInfoAbout", L"https://github.com/HaxOrWot/AerixLang");
    RegSetStr(HKEY_CURRENT_USER, uninst_key, L"InstallLocation", root.wstring());
    RegSetStr(HKEY_CURRENT_USER, uninst_key, L"DisplayIcon", (root / L"assets" / L"aerix.ico").wstring() + L",0");
    RegSetStr(HKEY_CURRENT_USER, uninst_key, L"UninstallString", L"\"" + uninst_exe + L"\" --uninstall");
    RegSetStr(HKEY_CURRENT_USER, uninst_key, L"QuietUninstallString", L"\"" + uninst_exe + L"\" --uninstall --silent");
    RegSetDword(HKEY_CURRENT_USER, uninst_key, L"NoModify", 1);
    RegSetDword(HKEY_CURRENT_USER, uninst_key, L"NoRepair", 1);

    fs::path vsix_path = root / L"editors" / (std::wstring(L"aerix-") + AERIX_VERSION_WSTR + L".vsix");
    fs::path ext_src = root / L"editors" / L"extension";
    std::wstring user_home = ExpandEnv(L"%USERPROFILE%");

    if (opts.install_vscode) {
        InstallExtensionToEditor(
            L"VS Code",
            DetectVSCodeCli(),
            vsix_path,
            ext_src,
            fs::path(user_home) / L".vscode" / L"extensions" / (std::wstring(L"aerix-lang.aerix-") + AERIX_VERSION_WSTR),
            progress,
            93);
    }

    if (opts.install_antigravity) {
        InstallExtensionToEditor(
            L"Antigravity IDE",
            DetectAntigravityCli(),
            vsix_path,
            ext_src,
            fs::path(user_home) / L".antigravity" / L"extensions" / (std::wstring(L"aerix-lang.aerix-") + AERIX_VERSION_WSTR),
            progress,
            98);
    }

    if (progress) progress(100, L"Installation complete!");
    return true;
}

std::wstring ResolveInstalledDirFromRegistry() {
    std::wstring loc = RegGetStr(HKEY_CURRENT_USER,
                                 L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AerixLang",
                                 L"InstallLocation");
    if (!loc.empty()) return loc;
    return RegGetStr(HKEY_CURRENT_USER, L"Environment", L"AERIX_HOME");
}

bool RunUninstall(const std::wstring& install_dir,
                  const ProgressCallback& progress,
                  std::wstring& error_out) {
    if (install_dir.empty()) {
        error_out = L"No Aerix installation directory found.";
        return false;
    }

    fs::path root = TrimTrailingSlashes(install_dir);
    if (progress) progress(20, L"Removing Aerix environment variables and PATH entry...");
    std::wstring cur_home = TrimTrailingSlashes(RegGetStr(HKEY_CURRENT_USER, L"Environment", L"AERIX_HOME"));
    if (ToLower(cur_home) == ToLower(root.wstring())) {
        RegDelValue(HKEY_CURRENT_USER, L"Environment", L"AERIX_HOME");
        RegDelValue(HKEY_CURRENT_USER, L"Environment", L"AERIX_STDLIB");
        RegDelValue(HKEY_CURRENT_USER, L"Environment", L"AERIX_STDLIB_PATH");
        RegDelValue(HKEY_CURRENT_USER, L"Environment", L"AERIX_MODULE_PATH");
    }
    RemoveUserPathEntry((root / L"bin").wstring());
    BroadcastEnvChange();

    if (progress) progress(45, L"Removing .arx file associations and Uninstall entry...");
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\Aerix.SourceFile");
    std::wstring ext_progid = RegGetStr(HKEY_CURRENT_USER, L"Software\\Classes\\.arx", nullptr);
    if (ext_progid == L"Aerix.SourceFile") {
        RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Classes\\.arx");
    }
    RegDeleteTreeW(HKEY_CURRENT_USER, L"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AerixLang");
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, nullptr, nullptr);

    if (progress) progress(75, L"Removing installed toolchain files...");
    std::error_code ec;
    for (const wchar_t* sub : {L"bin", L"stdlib", L"modules", L"editors", L"assets", L"docs"}) {
        fs::path p = root / sub;
        if (fs::exists(p, ec)) fs::remove_all(p, ec);
    }
    fs::path lic = root / L"LICENSE";
    if (fs::exists(lic, ec)) fs::remove(lic, ec);

    // Try removing root directly if Uninstall.exe is running from outside root
    wchar_t self_path[MAX_PATH] = {};
    GetModuleFileNameW(nullptr, self_path, MAX_PATH);
    fs::path self_fs(self_path);
    if (ToLower(self_fs.parent_path().wstring()) != ToLower(root.wstring())) {
        fs::path uninst = root / L"Uninstall.exe";
        if (fs::exists(uninst, ec)) fs::remove(uninst, ec);
        fs::remove(root, ec);
    }

    if (progress) progress(100, L"Aerix has been uninstalled.");
    return true;
}

void ScheduleSelfDeleteAndDirCleanup(const std::wstring& exe_path,
                                     const std::wstring& install_dir) {
    if (exe_path.empty()) return;
    std::wstring cmd = L"cmd.exe /C ping 127.0.0.1 -n 2 > nul & del /f /q \"" + exe_path + L"\"";
    if (!install_dir.empty()) {
        cmd += L" & rmdir \"" + TrimTrailingSlashes(install_dir) + L"\" 2>nul";
    }
    STARTUPINFOW si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi{};
    if (CreateProcessW(nullptr, cmd.data(), nullptr, nullptr, FALSE,
                       CREATE_NO_WINDOW | DETACHED_PROCESS, nullptr, nullptr, &si, &pi)) {
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
}
