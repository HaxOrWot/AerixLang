#pragma once

#include <functional>
#include <string>

struct InstallOptions {
    std::wstring install_dir;
    bool configure_env = true;
    bool file_associations = true;
    bool install_vscode = true;
    bool install_antigravity = true;
};

using ProgressCallback = std::function<void(int percent, const std::wstring& message)>;

std::wstring GetDefaultInstallDir();
std::wstring GetLicenseText(void* hInstance);
std::wstring DetectVSCodeCli();
std::wstring DetectAntigravityCli();

bool RunInstall(void* hInstance,
                const InstallOptions& opts,
                const ProgressCallback& progress,
                std::wstring& error_out);

bool RunUninstall(const std::wstring& install_dir,
                  const ProgressCallback& progress,
                  std::wstring& error_out);

std::wstring ResolveInstalledDirFromRegistry();
void ScheduleSelfDeleteAndDirCleanup(const std::wstring& exe_path,
                                     const std::wstring& install_dir);
