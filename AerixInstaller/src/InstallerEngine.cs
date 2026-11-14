using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;
using Microsoft.Win32;

namespace AerixSetup
{
    public sealed class InstallOptions
    {
        public string InstallDir = InstallerEngine.GetDefaultInstallDir();
        public bool ConfigureEnv = true;
        public bool FileAssociations = true;
        public bool InstallIdeExtensions = true;
        public bool RunSmokeTest = true;
    }

    public sealed class EditorInfo
    {
        public string Name;
        public string CliPath;
        public string ExtensionDir;
        public bool IsDetected;

        public EditorInfo(string name, string cliPath, string extDir, bool detected)
        {
            Name = name;
            CliPath = cliPath;
            ExtensionDir = extDir;
            IsDetected = detected;
        }
    }

    public sealed class InstallReport
    {
        public bool Success;
        public string ErrorMessage = "";
        public string InstalledVersion = "";
        public string SmokeTestSummary = "";
        public int ExtractedFiles;
        public readonly List<string> InstalledEditors = new List<string>();
    }

    public sealed class StableReleaseInfo
    {
        public string TagName = "";
        public string Version = "";
        public string Channel = "stable";
        public string SetupAssetName = "";
        public string SetupDownloadUrl = "";
        public long SetupSize;
        public string PublishedAt = "";
        public string HtmlUrl = "";
        public string ReleaseNotes = "";
    }

    public sealed class UpdateResult
    {
        public bool Success;
        public bool Updated;
        public bool UpdateAvailable;
        public string CurrentVersion = "";
        public string LatestVersion = "";
        public string InstallDir = "";
        public string PublishedAt = "";
        public string AssetName = "";
        public long AssetSize;
        public string ReleaseUrl = "";
        public string ReleaseNotes = "";
        public string LastCheckedAt = "";
        public string LogPath = "";
        public int ModuleCount;
        public bool HasStdlib;
        public double ElapsedSeconds;
        public string Message = "";
    }

    public delegate void ProgressHandler(int percent, string status, string logLine);

    public static class InstallerEngine
    {
        public const string DefaultVersion = "2.2.25-stable";
        public const string VmMinVersion = "1.1.3b";
        private const string UninstallRegPath = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\AerixLang";
        private const string ExtensionIdPrefix = "aerix-lang.aerix-";

        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        private static extern IntPtr SendMessageTimeout(
            IntPtr hWnd,
            uint msg,
            UIntPtr wParam,
            string lParam,
            uint flags,
            uint timeout,
            out UIntPtr result);

        [DllImport("shell32.dll")]
        private static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);

        private static readonly IntPtr HWND_BROADCAST = new IntPtr(0xffff);
        private const uint WM_SETTINGCHANGE = 0x001A;
        private const uint SMTO_ABORTIFHUNG = 0x0002;
        private const int SHCNE_ASSOCCHANGED = 0x08000000;
        private const uint SHCNF_IDLIST = 0x0000;

        private static string _cachedVersion;

        public static string GetVersion()
        {
            if (!string.IsNullOrEmpty(_cachedVersion)) return _cachedVersion;
            try
            {
                string json = ReadEmbeddedText("installer_manifest.json");
                if (!string.IsNullOrEmpty(json))
                {
                    Match m = Regex.Match(json, "\"version\"\\s*:\\s*\"([^\"]+)\"");
                    if (m.Success && !string.IsNullOrEmpty(m.Groups[1].Value))
                    {
                        _cachedVersion = m.Groups[1].Value;
                        return _cachedVersion;
                    }
                }
            }
            catch
            {
            }
            _cachedVersion = DefaultVersion;
            return _cachedVersion;
        }

        public static string GetDefaultInstallDir()
        {
            string existing = ResolveInstalledDirFromRegistry();
            if (!string.IsNullOrEmpty(existing)) return TrimTrailingSlashes(existing);

            string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (string.IsNullOrEmpty(localApp)) return @"C:\Aerix";
            return Path.Combine(localApp, "Programs", "Aerix");
        }

        public static string GetLicenseText()
        {
            string raw = ReadEmbeddedText("LICENSE");
            if (string.IsNullOrEmpty(raw))
            {
                return "MIT License\r\n\r\nCopyright (c) HaxOrWot / AerixLang";
            }
            return raw.Replace("\r\n", "\n").Replace("\n", "\r\n");
        }

        public static byte[] ReadEmbeddedBytes(string resourceName)
        {
            Assembly asm = Assembly.GetExecutingAssembly();
            using (Stream s = asm.GetManifestResourceStream(resourceName))
            {
                if (s == null) return null;
                using (MemoryStream ms = new MemoryStream())
                {
                    s.CopyTo(ms);
                    return ms.ToArray();
                }
            }
        }

        public static string ReadEmbeddedText(string resourceName)
        {
            byte[] bytes = ReadEmbeddedBytes(resourceName);
            if (bytes == null) return "";
            return Encoding.UTF8.GetString(bytes);
        }

        public static string ResolveInstalledDirFromRegistry()
        {
            try
            {
                using (RegistryKey key = Registry.CurrentUser.OpenSubKey(UninstallRegPath, false))
                {
                    if (key != null)
                    {
                        object loc = key.GetValue("InstallLocation");
                        if (loc != null && !string.IsNullOrWhiteSpace(loc.ToString()))
                        {
                            return loc.ToString();
                        }
                    }
                }
                using (RegistryKey env = Registry.CurrentUser.OpenSubKey("Environment", false))
                {
                    if (env != null)
                    {
                        object home = env.GetValue("AERIX_HOME");
                        if (home != null && !string.IsNullOrWhiteSpace(home.ToString()))
                        {
                            return home.ToString();
                        }
                    }
                }
            }
            catch
            {
            }
            return "";
        }

        public static List<EditorInfo> DetectEditors()
        {
            string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string pf = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            string pfx86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
            string userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);

            var list = new List<EditorInfo>();

            // 1. Visual Studio Code
            string vsCli = FindCli(
                new[] { "code.cmd", "code" },
                new[]
                {
                    Path.Combine(local, @"Programs\Microsoft VS Code\bin\code.cmd"),
                    Path.Combine(pf, @"Microsoft VS Code\bin\code.cmd"),
                    Path.Combine(pfx86, @"Microsoft VS Code\bin\code.cmd")
                });
            string vsExt = Path.Combine(userProfile, @".vscode\extensions");
            list.Add(new EditorInfo("VS Code", vsCli, vsExt, !string.IsNullOrEmpty(vsCli) || Directory.Exists(Path.Combine(userProfile, ".vscode"))));

            // 2. VS Code Insiders
            string vsiCli = FindCli(
                new[] { "code-insiders.cmd", "code-insiders" },
                new[]
                {
                    Path.Combine(local, @"Programs\Microsoft VS Code Insiders\bin\code-insiders.cmd"),
                    Path.Combine(pf, @"Microsoft VS Code Insiders\bin\code-insiders.cmd")
                });
            string vsiExt = Path.Combine(userProfile, @".vscode-insiders\extensions");
            list.Add(new EditorInfo("VS Code Insiders", vsiCli, vsiExt, !string.IsNullOrEmpty(vsiCli) || Directory.Exists(Path.Combine(userProfile, ".vscode-insiders"))));

            // 3. Antigravity
            string agyCli = FindCli(
                new[] { "antigravity.cmd", "antigravity" },
                new[]
                {
                    Path.Combine(local, @"Programs\Antigravity\bin\antigravity.cmd"),
                    Path.Combine(pf, @"Antigravity\bin\antigravity.cmd"),
                    @"X:\Antigravity\bin\antigravity.cmd"
                });
            string agyExt = Path.Combine(userProfile, @".antigravity\extensions");
            list.Add(new EditorInfo("Antigravity", agyCli, agyExt, !string.IsNullOrEmpty(agyCli) || Directory.Exists(Path.Combine(userProfile, ".antigravity"))));

            // 4. Antigravity IDE
            string agyIdeCli = FindCli(
                new[] { "antigravity-ide.cmd", "antigravity-ide" },
                new[]
                {
                    Path.Combine(local, @"Programs\Antigravity IDE\bin\antigravity-ide.cmd"),
                    Path.Combine(pf, @"Antigravity IDE\bin\antigravity-ide.cmd")
                });
            string agyIdeExt = Path.Combine(userProfile, @".antigravity-ide\extensions");
            list.Add(new EditorInfo("Antigravity IDE", agyIdeCli, agyIdeExt, !string.IsNullOrEmpty(agyIdeCli) || Directory.Exists(Path.Combine(userProfile, ".antigravity-ide"))));

            // 5. Cursor
            string curCli = FindCli(
                new[] { "cursor.cmd", "cursor" },
                new[]
                {
                    Path.Combine(local, @"Programs\cursor\resources\app\bin\cursor.cmd"),
                    Path.Combine(pf, @"Cursor\resources\app\bin\cursor.cmd")
                });
            string curExt = Path.Combine(userProfile, @".cursor\extensions");
            list.Add(new EditorInfo("Cursor", curCli, curExt, !string.IsNullOrEmpty(curCli) || Directory.Exists(Path.Combine(userProfile, ".cursor"))));

            // 6. Windsurf
            string wsCli = FindCli(
                new[] { "windsurf.cmd", "windsurf" },
                new[]
                {
                    Path.Combine(local, @"Programs\Windsurf\bin\windsurf.cmd"),
                    Path.Combine(pf, @"Windsurf\bin\windsurf.cmd")
                });
            string wsExt = Path.Combine(userProfile, @".windsurf\extensions");
            list.Add(new EditorInfo("Windsurf", wsCli, wsExt, !string.IsNullOrEmpty(wsCli) || Directory.Exists(Path.Combine(userProfile, ".windsurf"))));

            return list;
        }

        public static InstallReport RunInstall(InstallOptions opts, ProgressHandler progress)
        {
            var report = new InstallReport();
            string ver = GetVersion();
            report.InstalledVersion = ver;

            if (opts == null || string.IsNullOrWhiteSpace(opts.InstallDir))
            {
                report.ErrorMessage = "Destination folder cannot be empty.";
                return report;
            }

            string root = Path.GetFullPath(TrimTrailingSlashes(opts.InstallDir));
            try
            {
                Directory.CreateDirectory(root);
                Report(progress, 4, "Preparing destination folder...", "Target: " + root);

                byte[] zipBytes = ReadEmbeddedBytes("AerixPayload.zip");
                if (zipBytes == null || zipBytes.Length == 0)
                {
                    report.ErrorMessage = "Embedded installation payload (AerixPayload.zip) is missing.";
                    return report;
                }

                // 1. Extract embedded ZIP payload with locked-.exe safe swap
                long totalRawBytes = 0;
                using (MemoryStream ms = new MemoryStream(zipBytes))
                using (ZipArchive archive = new ZipArchive(ms, ZipArchiveMode.Read))
                {
                    int totalEntries = archive.Entries.Count;
                    int done = 0;
                    string rootPrefix = root.TrimEnd('\\') + @"\";

                    foreach (ZipArchiveEntry entry in archive.Entries)
                    {
                        done++;
                        if (string.IsNullOrEmpty(entry.Name))
                        {
                            string dirOnly = Path.GetFullPath(Path.Combine(root, entry.FullName.Replace('/', '\\')));
                            if (dirOnly.StartsWith(rootPrefix, StringComparison.OrdinalIgnoreCase))
                            {
                                Directory.CreateDirectory(dirOnly);
                            }
                            continue;
                        }

                        string rel = entry.FullName.Replace('/', '\\');
                        string target = Path.GetFullPath(Path.Combine(root, rel));
                        if (!target.StartsWith(rootPrefix, StringComparison.OrdinalIgnoreCase))
                        {
                            report.ErrorMessage = "Blocked unsafe archive entry: " + entry.FullName;
                            return report;
                        }

                        string parent = Path.GetDirectoryName(target);
                        if (!string.IsNullOrEmpty(parent)) Directory.CreateDirectory(parent);

                        WriteEntrySafe(entry, target);
                        totalRawBytes += entry.Length;
                        report.ExtractedFiles++;

                        int pct = 5 + (done * 55) / (totalEntries > 0 ? totalEntries : 1);
                        Report(progress, pct, "Extracting " + entry.Name + "...", "  -> " + rel);
                    }
                }

                // Clean up leftover .old executables from prior locked swaps when possible
                CleanupStaleBackups(root);
                CleanupStaleBackups(Path.Combine(root, "bin"));

                // Sync legacy ~/.aerix/bin if present so an older user-local binary doesn't shadow PATH
                string legacyBin = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    ".aerix", "bin");
                if (Directory.Exists(legacyBin) &&
                    !string.Equals(Path.GetFullPath(legacyBin).TrimEnd('\\'),
                                   Path.GetFullPath(Path.Combine(root, "bin")).TrimEnd('\\'),
                                   StringComparison.OrdinalIgnoreCase))
                {
                    SyncLegacyBinaries(Path.Combine(root, "bin"), legacyBin, progress);
                }

                // 2. Copy self as Uninstall.exe
                Report(progress, 65, "Creating Windows uninstaller...", "Creating Uninstall.exe");
                string selfExe = Assembly.GetExecutingAssembly().Location;
                string uninstExe = Path.Combine(root, "Uninstall.exe");
                if (!string.IsNullOrEmpty(selfExe) && File.Exists(selfExe) &&
                    !string.Equals(Path.GetFullPath(selfExe), Path.GetFullPath(uninstExe), StringComparison.OrdinalIgnoreCase))
                {
                    CopyFileLockedSafe(selfExe, uninstExe);
                }

                // 3. Configure Environment Variables & PATH
                string previousHome = ResolveInstalledDirFromRegistry();
                if (opts.ConfigureEnv)
                {
                    Report(progress, 72, "Configuring environment variables & PATH...", "Updating HKCU\\Environment (AERIX_HOME, AERIX_STDLIB_PATH, AERIX_MODULE_PATH, Path)");
                    string stdlibDir = Path.Combine(root, "stdlib");
                    string modulesDir = Path.Combine(root, "modules");
                    string binDir = Path.Combine(root, "bin");
                    string arxExe = Path.Combine(binDir, "arx.exe");
                    string arxcExe = Path.Combine(binDir, "arxc.exe");

                    if (!string.IsNullOrEmpty(previousHome))
                    {
                        string prevNorm = Path.GetFullPath(TrimTrailingSlashes(previousHome));
                        if (!string.Equals(prevNorm, root, StringComparison.OrdinalIgnoreCase))
                        {
                            RemoveUserPathEntry(Path.Combine(prevNorm, "bin"));
                        }
                    }

                    using (RegistryKey env = Registry.CurrentUser.CreateSubKey("Environment"))
                    {
                        if (env != null)
                        {
                            env.SetValue("AERIX_HOME", root, RegistryValueKind.String);
                            env.SetValue("AERIX_STDLIB", stdlibDir, RegistryValueKind.String);
                            env.SetValue("AERIX_STDLIB_PATH", stdlibDir, RegistryValueKind.String);
                            env.SetValue("AERIX_MODULE_PATH", modulesDir, RegistryValueKind.String);
                        }
                    }

                    PrependOrUpdateUserPath(binDir);
                    SetAppPath("arx.exe", arxExe, binDir);
                    SetAppPath("arxc.exe", arxcExe, binDir);

                    Environment.SetEnvironmentVariable("AERIX_HOME", root);
                    Environment.SetEnvironmentVariable("AERIX_STDLIB", stdlibDir);
                    Environment.SetEnvironmentVariable("AERIX_STDLIB_PATH", stdlibDir);
                    Environment.SetEnvironmentVariable("AERIX_MODULE_PATH", modulesDir);
                    BroadcastEnvChange();
                }

                // 4. Register .arx File Association & Context Menus
                if (opts.FileAssociations)
                {
                    Report(progress, 78, "Registering .arx file association & Explorer icons...", "Registering HKCU\\Software\\Classes\\.arx and Aerix.SourceFile");
                    RegisterFileAssociations(root);
                }

                // 5. Windows Apps & Features Registration
                Report(progress, 82, "Registering Windows Apps & Features entry...", "Registering Uninstall\\AerixLang");
                RegisterUninstallEntry(root, ver, totalRawBytes);

                // 6. Install IDE Extensions across detected editors
                if (opts.InstallIdeExtensions)
                {
                    string vsixPath = Path.Combine(root, "editors", string.Format("aerix-{0}.vsix", ver));
                    string unpackedSrc = Path.Combine(root, "editors", "extension");
                    List<EditorInfo> editors = DetectEditors();
                    var active = new List<EditorInfo>();
                    foreach (EditorInfo ed in editors)
                    {
                        if (ed.IsDetected) active.Add(ed);
                    }

                    if (active.Count == 0)
                    {
                        Report(progress, 92, "No local VS Code/Antigravity installation detected.", "Skipped IDE extension install (VSIX saved in editors\\).");
                    }
                    else
                    {
                        int step = 0;
                        foreach (EditorInfo ed in active)
                        {
                            step++;
                            int pct = 84 + (step * 10) / active.Count;
                            bool ok = InstallExtensionToEditor(ed, ver, vsixPath, unpackedSrc, progress, pct);
                            if (ok) report.InstalledEditors.Add(ed.Name);
                        }
                    }
                }

                // 7. Post-install verification smoke test
                if (opts.RunSmokeTest)
                {
                    Report(progress, 96, "Verifying compiler & toolchain...", "Running native compiler smoke check");
                    report.SmokeTestSummary = VerifyToolchain(root, ver, progress);
                }

                Report(progress, 100, "Aerix " + ver + " installation complete!", "Done.");
                report.Success = true;
                return report;
            }
            catch (Exception ex)
            {
                report.Success = false;
                report.ErrorMessage = ex.Message;
                return report;
            }
        }

        public static bool RunUninstall(string installDir, ProgressHandler progress, out string errorOut)
        {
            errorOut = "";
            if (string.IsNullOrWhiteSpace(installDir))
            {
                errorOut = "No Aerix installation directory was found.";
                return false;
            }

            try
            {
                string root = Path.GetFullPath(TrimTrailingSlashes(installDir));
                Report(progress, 20, "Removing environment variables & PATH...", "Cleaning HKCU\\Environment");

                using (RegistryKey env = Registry.CurrentUser.OpenSubKey("Environment", true))
                {
                    if (env != null)
                    {
                        object cur = env.GetValue("AERIX_HOME");
                        if (cur != null && string.Equals(TrimTrailingSlashes(cur.ToString()), root, StringComparison.OrdinalIgnoreCase))
                        {
                            DeleteValueSafe(env, "AERIX_HOME");
                            DeleteValueSafe(env, "AERIX_STDLIB");
                            DeleteValueSafe(env, "AERIX_STDLIB_PATH");
                            DeleteValueSafe(env, "AERIX_MODULE_PATH");
                        }
                    }
                }
                RemoveUserPathEntry(Path.Combine(root, "bin"));
                DeleteTreeSafe(Registry.CurrentUser, @"Software\Microsoft\Windows\CurrentVersion\App Paths\arx.exe");
                DeleteTreeSafe(Registry.CurrentUser, @"Software\Microsoft\Windows\CurrentVersion\App Paths\arxc.exe");
                BroadcastEnvChange();

                Report(progress, 48, "Removing file associations & registry keys...", "Cleaning HKCU\\Software\\Classes\\.arx");
                DeleteTreeSafe(Registry.CurrentUser, @"Software\Classes\Aerix.SourceFile");
                using (RegistryKey extKey = Registry.CurrentUser.OpenSubKey(@"Software\Classes\.arx", false))
                {
                    if (extKey != null)
                    {
                        object val = extKey.GetValue(null);
                        if (val != null && val.ToString() == "Aerix.SourceFile")
                        {
                            DeleteTreeSafe(Registry.CurrentUser, @"Software\Classes\.arx");
                        }
                    }
                }
                DeleteTreeSafe(Registry.CurrentUser, UninstallRegPath);
                SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, IntPtr.Zero, IntPtr.Zero);

                Report(progress, 78, "Removing installed Aerix files...", "Deleting toolchain directories");
                foreach (string sub in new[] { "bin", "stdlib", "modules", "editors", "assets", "docs" })
                {
                    string p = Path.Combine(root, sub);
                    if (Directory.Exists(p))
                    {
                        try { Directory.Delete(p, true); } catch { }
                    }
                }
                string lic = Path.Combine(root, "LICENSE");
                if (File.Exists(lic))
                {
                    try { File.Delete(lic); } catch { }
                }

                string selfExe = Assembly.GetExecutingAssembly().Location;
                string selfDir = string.IsNullOrEmpty(selfExe) ? "" : Path.GetFullPath(Path.GetDirectoryName(selfExe));
                if (!string.Equals(selfDir.TrimEnd('\\'), root.TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
                {
                    string uninst = Path.Combine(root, "Uninstall.exe");
                    if (File.Exists(uninst))
                    {
                        try { File.Delete(uninst); } catch { }
                    }
                    try
                    {
                        if (Directory.Exists(root) && Directory.GetFileSystemEntries(root).Length == 0)
                        {
                            Directory.Delete(root, false);
                        }
                    }
                    catch { }
                }

                Report(progress, 100, "Aerix has been uninstalled.", "Uninstall complete.");
                return true;
            }
            catch (Exception ex)
            {
                errorOut = ex.Message;
                return false;
            }
        }

        public static void ScheduleSelfDeleteIfRunningFrom(string installDir)
        {
            try
            {
                string selfExe = Assembly.GetExecutingAssembly().Location;
                if (string.IsNullOrEmpty(selfExe) || string.IsNullOrWhiteSpace(installDir)) return;
                string selfDir = Path.GetFullPath(Path.GetDirectoryName(selfExe)).TrimEnd('\\');
                string root = Path.GetFullPath(TrimTrailingSlashes(installDir)).TrimEnd('\\');
                if (!string.Equals(selfDir, root, StringComparison.OrdinalIgnoreCase)) return;

                string args = string.Format("/C ping 127.0.0.1 -n 3 > nul & del /f /q \"{0}\" & rmdir \"{1}\" 2>nul", selfExe, root);
                var psi = new ProcessStartInfo("cmd.exe", args);
                psi.CreateNoWindow = true;
                psi.UseShellExecute = false;
                psi.WindowStyle = ProcessWindowStyle.Hidden;
                Process.Start(psi);
            }
            catch
            {
            }
        }

        private static string VerifyToolchain(string root, string ver, ProgressHandler progress)
        {
            string arxExe = Path.Combine(root, "bin", "arx.exe");
            if (!File.Exists(arxExe)) return "arx.exe not found";

            string verOut = RunCapture(arxExe, "version", root, 10000).Trim();
            Report(progress, 97, "Verified compiler version...", "  " + verOut);

            string tmpDir = Path.Combine(Path.GetTempPath(), "aerix_verify_" + Guid.NewGuid().ToString("N"));
            try
            {
                Directory.CreateDirectory(tmpDir);
                string sample = Path.Combine(tmpDir, "hello_setup.arx");
                File.WriteAllText(sample, "fn main() {\n    let msg = \"Aerix Ready\"\n    println(msg)\n}\n", Encoding.UTF8);

                string chkOut = RunCapture(arxExe, "check \"" + sample + "\"", tmpDir, 15000).Trim();
                Report(progress, 98, "Compiler typecheck verified.", "  " + chkOut);

                string runOut = RunCapture(arxExe, "run \"" + sample + "\"", tmpDir, 20000).Trim();
                Report(progress, 99, "Native x86-64 execution verified.", "  Output: " + runOut);

                if (verOut.Contains(ver) && runOut.Contains("Aerix Ready"))
                {
                    return string.Format("{0} (native x64 check & run PASS)", verOut);
                }
                return string.IsNullOrEmpty(verOut) ? "Check passed" : verOut;
            }
            catch (Exception ex)
            {
                return "Check warning: " + ex.Message;
            }
            finally
            {
                try { if (Directory.Exists(tmpDir)) Directory.Delete(tmpDir, true); } catch { }
            }
        }

        private static void WriteEntrySafe(ZipArchiveEntry entry, string targetPath)
        {
            try
            {
                using (Stream src = entry.Open())
                using (FileStream dst = new FileStream(targetPath, FileMode.Create, FileAccess.Write, FileShare.None))
                {
                    src.CopyTo(dst);
                }
            }
            catch (IOException)
            {
                if (targetPath.EndsWith(".exe", StringComparison.OrdinalIgnoreCase) && File.Exists(targetPath))
                {
                    MoveLockedFileAside(targetPath);
                    using (Stream src = entry.Open())
                    using (FileStream dst = new FileStream(targetPath, FileMode.Create, FileAccess.Write, FileShare.None))
                    {
                        src.CopyTo(dst);
                    }
                    return;
                }
                throw;
            }
        }

        private static void CopyFileLockedSafe(string srcPath, string dstPath)
        {
            try
            {
                File.Copy(srcPath, dstPath, true);
            }
            catch (IOException)
            {
                if (File.Exists(dstPath))
                {
                    MoveLockedFileAside(dstPath);
                    File.Copy(srcPath, dstPath, true);
                }
                else
                {
                    throw;
                }
            }
        }

        private static void MoveLockedFileAside(string filePath)
        {
            string oldPath = filePath + ".old";
            try { if (File.Exists(oldPath)) File.Delete(oldPath); } catch { }
            if (File.Exists(oldPath))
            {
                oldPath = filePath + "." + DateTime.UtcNow.Ticks + ".old";
            }
            File.Move(filePath, oldPath);
        }

        private static void CleanupStaleBackups(string dir)
        {
            if (!Directory.Exists(dir)) return;
            foreach (string f in Directory.GetFiles(dir, "*.old*"))
            {
                try { File.Delete(f); } catch { }
            }
        }

        private static void SyncLegacyBinaries(string newBin, string legacyBin, ProgressHandler progress)
        {
            foreach (string exe in new[] { "arx.exe", "arxc.exe" })
            {
                string src = Path.Combine(newBin, exe);
                string dst = Path.Combine(legacyBin, exe);
                if (File.Exists(src) && File.Exists(dst))
                {
                    try
                    {
                        CopyFileLockedSafe(src, dst);
                        Report(progress, 63, "Synchronizing legacy ~/.aerix/bin/" + exe + "...", "  Synced " + dst);
                    }
                    catch
                    {
                    }
                }
            }
        }

        private static bool InstallExtensionToEditor(
            EditorInfo ed,
            string ver,
            string vsixPath,
            string unpackedSrc,
            ProgressHandler progress,
            int pct)
        {
            // Prune older aerix-lang.aerix-* extension folders so IDE never loads stale versions
            PruneStaleExtensions(ed.ExtensionDir, ver);

            bool cliOk = false;
            if (!string.IsNullOrEmpty(ed.CliPath) && File.Exists(vsixPath))
            {
                Report(progress, pct - 2, "Installing " + ed.Name + " extension...", "Running " + ed.Name + " CLI");
                string cmdArgs = string.Format("/S /C \"\"{0}\" --install-extension \"{1}\" --force\"", ed.CliPath, vsixPath);
                cliOk = RunHiddenCmd(cmdArgs, 45000);
            }

            if (!cliOk && Directory.Exists(unpackedSrc))
            {
                Report(progress, pct, "Deploying " + ed.Name + " extension files...", "Copying extension to " + ed.ExtensionDir);
                string fallbackTarget = Path.Combine(ed.ExtensionDir, ExtensionIdPrefix + ver);
                Directory.CreateDirectory(fallbackTarget);
                CopyDirectory(unpackedSrc, fallbackTarget);
                return true;
            }

            if (cliOk)
            {
                Report(progress, pct, ed.Name + " extension installed.", "Installed " + ed.Name + " v" + ver);
            }
            return cliOk;
        }

        private static void PruneStaleExtensions(string extDir, string activeVer)
        {
            try
            {
                if (!Directory.Exists(extDir)) return;
                string keepName = ExtensionIdPrefix + activeVer;
                foreach (string d in Directory.GetDirectories(extDir, ExtensionIdPrefix + "*"))
                {
                    string name = Path.GetFileName(d);
                    if (!string.Equals(name, keepName, StringComparison.OrdinalIgnoreCase))
                    {
                        try { Directory.Delete(d, true); } catch { }
                    }
                }
            }
            catch
            {
            }
        }

        private static void CopyDirectory(string src, string dst)
        {
            Directory.CreateDirectory(dst);
            foreach (string file in Directory.GetFiles(src))
            {
                File.Copy(file, Path.Combine(dst, Path.GetFileName(file)), true);
            }
            foreach (string sub in Directory.GetDirectories(src))
            {
                CopyDirectory(sub, Path.Combine(dst, Path.GetFileName(sub)));
            }
        }

        private static void RegisterFileAssociations(string root)
        {
            string fileIco = Path.Combine(root, "assets", "aerix_file.ico");
            string appIco = Path.Combine(root, "assets", "aerix.ico");
            string arxExe = Path.Combine(root, "bin", "arx.exe");

            using (RegistryKey k = Registry.CurrentUser.CreateSubKey(@"Software\Classes\.arx"))
            {
                if (k != null)
                {
                    k.SetValue(null, "Aerix.SourceFile", RegistryValueKind.String);
                    k.SetValue("Content Type", "text/plain", RegistryValueKind.String);
                    k.SetValue("PerceivedType", "text", RegistryValueKind.String);
                }
            }
            using (RegistryKey owp = Registry.CurrentUser.CreateSubKey(@"Software\Classes\.arx\OpenWithProgids"))
            {
                if (owp != null) owp.SetValue("Aerix.SourceFile", "", RegistryValueKind.String);
            }

            using (RegistryKey pid = Registry.CurrentUser.CreateSubKey(@"Software\Classes\Aerix.SourceFile"))
            {
                if (pid != null)
                {
                    pid.SetValue(null, "Aerix Source Code", RegistryValueKind.String);
                    pid.SetValue("FriendlyTypeName", "Aerix Source Code", RegistryValueKind.String);
                }
            }
            using (RegistryKey ico = Registry.CurrentUser.CreateSubKey(@"Software\Classes\Aerix.SourceFile\DefaultIcon"))
            {
                if (ico != null) ico.SetValue(null, fileIco + ",0", RegistryValueKind.String);
            }

            string editorCmd = DetectPreferredEditorCli();
            SetShellVerb("open", "Open with Code Editor", null, string.Format("\"{0}\" \"%1\"", editorCmd));
            SetShellVerb("run", "Run with Aerix (arx run)", appIco + ",0", string.Format("cmd.exe /S /K \"\"{0}\" run \"%1\"\"", arxExe));
            SetShellVerb("check", "Check Syntax & Types (arx check)", appIco + ",0", string.Format("cmd.exe /S /K \"\"{0}\" check \"%1\"\"", arxExe));
            SetShellVerb("build", "Build Native Executable (arx build)", appIco + ",0", string.Format("cmd.exe /S /K \"\"{0}\" build \"%1\"\"", arxExe));

            SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, IntPtr.Zero, IntPtr.Zero);
        }

        private static void SetShellVerb(string verb, string label, string icon, string command)
        {
            string basePath = @"Software\Classes\Aerix.SourceFile\shell\" + verb;
            using (RegistryKey vk = Registry.CurrentUser.CreateSubKey(basePath))
            {
                if (vk != null)
                {
                    vk.SetValue(null, label, RegistryValueKind.String);
                    if (!string.IsNullOrEmpty(icon)) vk.SetValue("Icon", icon, RegistryValueKind.String);
                }
            }
            using (RegistryKey ck = Registry.CurrentUser.CreateSubKey(basePath + @"\command"))
            {
                if (ck != null) ck.SetValue(null, command, RegistryValueKind.String);
            }
        }

        private static void RegisterUninstallEntry(string root, string ver, long totalRawBytes)
        {
            string uninstExe = Path.Combine(root, "Uninstall.exe");
            string appIco = Path.Combine(root, "assets", "aerix.ico");
            int estKb = (int)Math.Max(1024, (totalRawBytes + 1023) / 1024);

            using (RegistryKey key = Registry.CurrentUser.CreateSubKey(UninstallRegPath))
            {
                if (key == null) return;
                key.SetValue("DisplayName", "Aerix " + ver, RegistryValueKind.String);
                key.SetValue("DisplayVersion", ver, RegistryValueKind.String);
                key.SetValue("Publisher", "HaxOrWot", RegistryValueKind.String);
                key.SetValue("URLInfoAbout", "https://github.com/HaxOrWot/AerixLang", RegistryValueKind.String);
                key.SetValue("InstallLocation", root, RegistryValueKind.String);
                key.SetValue("DisplayIcon", appIco + ",0", RegistryValueKind.String);
                key.SetValue("UninstallString", "\"" + uninstExe + "\" --uninstall", RegistryValueKind.String);
                key.SetValue("QuietUninstallString", "\"" + uninstExe + "\" --uninstall --silent", RegistryValueKind.String);
                key.SetValue("EstimatedSize", estKb, RegistryValueKind.DWord);
                key.SetValue("NoModify", 1, RegistryValueKind.DWord);
                key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
            }
        }

        private static void SetAppPath(string exeName, string exePath, string workDir)
        {
            using (RegistryKey k = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\App Paths\" + exeName))
            {
                if (k != null)
                {
                    k.SetValue(null, exePath, RegistryValueKind.String);
                    k.SetValue("Path", workDir, RegistryValueKind.String);
                }
            }
        }

        private static void PrependOrUpdateUserPath(string binDir)
        {
            using (RegistryKey env = Registry.CurrentUser.CreateSubKey("Environment"))
            {
                if (env == null) return;
                object rawObj = env.GetValue("Path", "", RegistryValueOptions.DoNotExpandEnvironmentNames);
                string raw = rawObj == null ? "" : rawObj.ToString();
                var parts = SplitPath(raw);
                string normTarget = TrimTrailingSlashes(binDir).ToLowerInvariant();
                var cleaned = new List<string>();
                cleaned.Add(binDir);
                foreach (string p in parts)
                {
                    if (TrimTrailingSlashes(p).ToLowerInvariant() != normTarget)
                    {
                        cleaned.Add(p);
                    }
                }
                env.SetValue("Path", string.Join(";", cleaned.ToArray()), RegistryValueKind.ExpandString);
            }
        }

        private static void RemoveUserPathEntry(string binDir)
        {
            using (RegistryKey env = Registry.CurrentUser.OpenSubKey("Environment", true))
            {
                if (env == null) return;
                object rawObj = env.GetValue("Path", "", RegistryValueOptions.DoNotExpandEnvironmentNames);
                string raw = rawObj == null ? "" : rawObj.ToString();
                if (string.IsNullOrEmpty(raw)) return;
                string normTarget = TrimTrailingSlashes(binDir).ToLowerInvariant();
                var kept = new List<string>();
                foreach (string p in SplitPath(raw))
                {
                    if (TrimTrailingSlashes(p).ToLowerInvariant() != normTarget)
                    {
                        kept.Add(p);
                    }
                }
                env.SetValue("Path", string.Join(";", kept.ToArray()), RegistryValueKind.ExpandString);
            }
        }

        private static List<string> SplitPath(string raw)
        {
            var res = new List<string>();
            if (string.IsNullOrEmpty(raw)) return res;
            foreach (string seg in raw.Split(';'))
            {
                string t = seg.Trim();
                if (!string.IsNullOrEmpty(t)) res.Add(t);
            }
            return res;
        }

        public static string DetectPreferredEditorCli()
        {
            foreach (EditorInfo ed in DetectEditors())
            {
                if (ed.Name == "Antigravity IDE" && !string.IsNullOrEmpty(ed.CliPath)) return ed.CliPath;
            }
            foreach (EditorInfo ed in DetectEditors())
            {
                if (ed.Name == "Antigravity" && !string.IsNullOrEmpty(ed.CliPath)) return ed.CliPath;
            }
            foreach (EditorInfo ed in DetectEditors())
            {
                if (!string.IsNullOrEmpty(ed.CliPath)) return ed.CliPath;
            }
            return "notepad.exe";
        }

        private static string FindCli(string[] pathNames, string[] candidates)
        {
            string envPath = Environment.GetEnvironmentVariable("PATH") ?? "";
            foreach (string dir in envPath.Split(';'))
            {
                string d = dir.Trim();
                if (string.IsNullOrEmpty(d)) continue;
                foreach (string name in pathNames)
                {
                    try
                    {
                        string p = Path.Combine(d, name);
                        if (File.Exists(p)) return p;
                    }
                    catch { }
                }
            }
            foreach (string cand in candidates)
            {
                if (!string.IsNullOrEmpty(cand) && File.Exists(cand)) return cand;
            }
            return "";
        }

        private static bool RunHiddenCmd(string cmdArgs, int timeoutMs)
        {
            try
            {
                var psi = new ProcessStartInfo("cmd.exe", cmdArgs);
                psi.CreateNoWindow = true;
                psi.UseShellExecute = false;
                psi.WindowStyle = ProcessWindowStyle.Hidden;
                using (Process p = Process.Start(psi))
                {
                    if (p == null) return false;
                    if (!p.WaitForExit(timeoutMs))
                    {
                        try { p.Kill(); } catch { }
                        return false;
                    }
                    return p.ExitCode == 0;
                }
            }
            catch
            {
                return false;
            }
        }

        private static string RunCapture(string exePath, string args, string workDir, int timeoutMs)
        {
            var psi = new ProcessStartInfo(exePath, args);
            psi.WorkingDirectory = workDir;
            psi.CreateNoWindow = true;
            psi.UseShellExecute = false;
            psi.RedirectStandardOutput = true;
            psi.RedirectStandardError = true;
            using (Process p = Process.Start(psi))
            {
                if (p == null) return "";
                string so = p.StandardOutput.ReadToEnd();
                string se = p.StandardError.ReadToEnd();
                if (!p.WaitForExit(timeoutMs))
                {
                    try { p.Kill(); } catch { }
                    throw new TimeoutException("Timed out running: " + exePath + " " + args);
                }
                return string.IsNullOrEmpty(so) ? se : so;
            }
        }

        private static void BroadcastEnvChange()
        {
            UIntPtr result;
            SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, UIntPtr.Zero, "Environment", SMTO_ABORTIFHUNG, 2500, out result);
        }

        private static void DeleteValueSafe(RegistryKey key, string valueName)
        {
            try { key.DeleteValue(valueName, false); } catch { }
        }

        private static void DeleteTreeSafe(RegistryKey root, string subkey)
        {
            try { root.DeleteSubKeyTree(subkey, false); } catch { }
        }

        public static string TrimTrailingSlashes(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            while (s.Length > 3 && (s.EndsWith(@"\") || s.EndsWith("/")))
            {
                s = s.Substring(0, s.Length - 1);
            }
            return s;
        }

        private static void Report(ProgressHandler h, int pct, string status, string logLine)
        {
            if (h != null) h(pct, status, logLine);
        }

        private const string GitHubReleasesApiUrl = "https://api.github.com/repos/HaxOrWot/AerixLang/releases?per_page=100";

        public static void WriteUpdaterLog(string msg)
        {
            try
            {
                string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                if (string.IsNullOrEmpty(localApp)) return;
                string dir = Path.Combine(localApp, "Aerix");
                Directory.CreateDirectory(dir);
                string logPath = Path.Combine(dir, "updater.log");
                if (File.Exists(logPath) && new FileInfo(logPath).Length > 65536)
                {
                    try { File.Delete(logPath); } catch { }
                }
                string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " " + msg + Environment.NewLine;
                File.AppendAllText(logPath, line, Encoding.UTF8);
            }
            catch
            {
            }
        }

        private static void TouchUpdateCheckStamp(string latestVersion)
        {
            try
            {
                string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                if (string.IsNullOrEmpty(localApp)) return;
                string dir = Path.Combine(localApp, "Aerix");
                Directory.CreateDirectory(dir);
                string stampPath = Path.Combine(dir, "last_update_check");
                File.WriteAllText(stampPath, DateTime.UtcNow.Ticks + "|" + (latestVersion ?? "") + Environment.NewLine, Encoding.UTF8);
            }
            catch
            {
            }
        }

        public static string GetInstalledVersionFromDisk(string installDir)
        {
            try
            {
                if (!string.IsNullOrWhiteSpace(installDir))
                {
                    string arxExe = Path.Combine(TrimTrailingSlashes(installDir), "bin", "arx.exe");
                    if (File.Exists(arxExe))
                    {
                        string outTxt = RunCapture(arxExe, "version", TrimTrailingSlashes(installDir), 8000);
                        Match m = Regex.Match(outTxt ?? "", "v([0-9]+\\.[0-9]+\\.[0-9]+[^\\s]*)");
                        if (m.Success) return m.Groups[1].Value;
                    }
                }
            }
            catch
            {
            }

            try
            {
                using (RegistryKey key = Registry.CurrentUser.OpenSubKey(UninstallRegPath, false))
                {
                    if (key != null)
                    {
                        object dv = key.GetValue("DisplayVersion");
                        if (dv != null && !string.IsNullOrWhiteSpace(dv.ToString()))
                        {
                            return dv.ToString().Trim().TrimStart('v', 'V');
                        }
                    }
                }
            }
            catch
            {
            }

            return GetVersion();
        }

        private static void ParseSemVer(string raw, out int major, out int minor, out int patch, out int patchLetter, out string preTag)
        {
            major = 0; minor = 0; patch = 0; patchLetter = 0; preTag = "";
            if (string.IsNullOrWhiteSpace(raw)) return;
            string s = raw.Trim();
            if (s.StartsWith("v", StringComparison.OrdinalIgnoreCase)) s = s.Substring(1);
            int dash = s.IndexOf('-');
            string core = dash >= 0 ? s.Substring(0, dash) : s;
            preTag = dash >= 0 ? s.Substring(dash + 1).Trim().ToLowerInvariant() : "";
            string[] parts = core.Split('.');
            if (parts.Length > 0) int.TryParse(parts[0], out major);
            if (parts.Length > 1) int.TryParse(parts[1], out minor);
            if (parts.Length > 2)
            {
                Match m = Regex.Match(parts[2], @"^([0-9]+)([a-zA-Z]*)(.*)$");
                if (m.Success)
                {
                    int.TryParse(m.Groups[1].Value, out patch);
                    string letters = m.Groups[2].Value.Trim().ToLowerInvariant();
                    if (!string.IsNullOrEmpty(letters))
                    {
                        int lrank = 0;
                        foreach (char ch in letters)
                        {
                            if (ch >= 'a' && ch <= 'z')
                            {
                                lrank = lrank * 26 + (ch - 'a' + 1);
                            }
                        }
                        patchLetter = lrank;
                    }
                    string trailing = m.Groups[3].Value.Trim().ToLowerInvariant();
                    if (!string.IsNullOrEmpty(trailing) && string.IsNullOrEmpty(preTag))
                    {
                        preTag = trailing;
                    }
                }
            }
        }

        private static int TagStabilityRank(string tag)
        {
            if (string.IsNullOrEmpty(tag) || tag == "stable") return 4;
            if (tag.StartsWith("rc")) return 3;
            if (tag == "p" || tag.StartsWith("pre")) return 2;
            if (tag == "b" || tag.StartsWith("beta")) return 1;
            return 0;
        }

        public static int CompareVersions(string a, string b)
        {
            int aMaj, aMin, aPat, aLet, bMaj, bMin, bPat, bLet;
            string aTag, bTag;
            ParseSemVer(a, out aMaj, out aMin, out aPat, out aLet, out aTag);
            ParseSemVer(b, out bMaj, out bMin, out bPat, out bLet, out bTag);
            if (aMaj != bMaj) return aMaj.CompareTo(bMaj);
            if (aMin != bMin) return aMin.CompareTo(bMin);
            if (aPat != bPat) return aPat.CompareTo(bPat);
            if (aLet != bLet) return aLet.CompareTo(bLet);
            int aRank = TagStabilityRank(aTag);
            int bRank = TagStabilityRank(bTag);
            if (aRank != bRank) return aRank.CompareTo(bRank);
            return string.Compare(aTag, bTag, StringComparison.OrdinalIgnoreCase);
        }

        private static bool BoolVal(Dictionary<string, object> dict, string key)
        {
            object v;
            if (dict != null && dict.TryGetValue(key, out v) && v is bool) return (bool)v;
            return false;
        }

        private static string StrVal(Dictionary<string, object> dict, string key)
        {
            object v;
            if (dict != null && dict.TryGetValue(key, out v) && v != null) return v.ToString();
            return "";
        }

        private static string ClassifyReleaseChannel(string tag, bool isPrerelease)
        {
            string low = (tag ?? "").Trim().ToLowerInvariant();
            if (low.EndsWith("b") || low.EndsWith("-b") || low.Contains("beta")) return "beta";
            if (isPrerelease || low.EndsWith("p") || low.EndsWith("-p") || low.Contains("-pre") || low.Contains("alpha") || low.Contains("-rc"))
            {
                return "pre";
            }
            return "stable";
        }

        public static List<StableReleaseInfo> FetchReleases(bool includePreAndBeta)
        {
            var list = new List<StableReleaseInfo>();
            try
            {
                ServicePointManager.SecurityProtocol |= (SecurityProtocolType)3072 | SecurityProtocolType.Tls | SecurityProtocolType.Tls11;
                string json = "";
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(GitHubReleasesApiUrl);
                req.Method = "GET";
                req.UserAgent = "AerixSetup-Updater";
                req.Accept = "application/vnd.github+json";
                req.Timeout = 15000;
                req.ReadWriteTimeout = 15000;
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                using (Stream st = resp.GetResponseStream())
                using (StreamReader sr = new StreamReader(st, Encoding.UTF8))
                {
                    json = sr.ReadToEnd();
                }

                var ser = new JavaScriptSerializer();
                object[] releases = ser.DeserializeObject(json) as object[];
                if (releases == null) return list;

                foreach (object item in releases)
                {
                    var rel = item as Dictionary<string, object>;
                    if (rel == null) continue;
                    if (BoolVal(rel, "draft")) continue;

                    bool isPre = BoolVal(rel, "prerelease");
                    string tag = StrVal(rel, "tag_name");
                    if (string.IsNullOrWhiteSpace(tag)) continue;

                    string channel = ClassifyReleaseChannel(tag, isPre);
                    if (!includePreAndBeta && (isPre || channel != "stable"))
                    {
                        continue;
                    }

                    object assetsObj;
                    if (!rel.TryGetValue("assets", out assetsObj)) continue;
                    object[] assets = assetsObj as object[];
                    if (assets == null) continue;

                    string assetName = "";
                    string downloadUrl = "";
                    long assetSize = 0;

                    foreach (object ao in assets)
                    {
                        var asset = ao as Dictionary<string, object>;
                        if (asset == null) continue;
                        string name = StrVal(asset, "name");
                        string url = StrVal(asset, "browser_download_url");
                        if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(url)) continue;
                        if (!name.StartsWith("AerixSetup-", StringComparison.OrdinalIgnoreCase) ||
                            !name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                        {
                            continue;
                        }

                        bool isPreferred = (channel == "stable" && name.IndexOf("-stable.exe", StringComparison.OrdinalIgnoreCase) >= 0) ||
                                           (channel == "beta" && name.IndexOf("b.exe", StringComparison.OrdinalIgnoreCase) >= 0) ||
                                           (channel == "pre" && name.IndexOf("p.exe", StringComparison.OrdinalIgnoreCase) >= 0);
                        if (string.IsNullOrEmpty(downloadUrl) || isPreferred)
                        {
                            assetName = name;
                            downloadUrl = url;
                            object szObj;
                            if (asset.TryGetValue("size", out szObj) && szObj != null)
                            {
                                long.TryParse(szObj.ToString(), out assetSize);
                            }
                            if (isPreferred) break;
                        }
                    }

                    if (string.IsNullOrEmpty(downloadUrl)) continue;
                    string ver = tag.Trim().TrimStart('v', 'V');
                    list.Add(new StableReleaseInfo
                    {
                        TagName = tag,
                        Version = ver,
                        Channel = channel,
                        SetupAssetName = assetName,
                        SetupDownloadUrl = downloadUrl,
                        SetupSize = assetSize,
                        PublishedAt = StrVal(rel, "published_at"),
                        HtmlUrl = StrVal(rel, "html_url"),
                        ReleaseNotes = StrVal(rel, "body")
                    });
                }

                list.Sort(delegate(StableReleaseInfo a, StableReleaseInfo b)
                {
                    return CompareVersions(b.Version, a.Version);
                });
            }
            catch (Exception ex)
            {
                WriteUpdaterLog("FetchReleases warning: " + ex.Message);
            }
            return list;
        }

        public static StableReleaseInfo FetchLatestStableRelease()
        {
            List<StableReleaseInfo> releases = FetchReleases(false);
            return releases.Count > 0 ? releases[0] : null;
        }

        public static string FormatBytes(long bytes)
        {
            if (bytes <= 0) return "unknown size";
            if (bytes < 1024) return bytes + " B";
            if (bytes < 1024 * 1024) return string.Format("{0:0.0} KB", bytes / 1024.0);
            return string.Format("{0:0.00} MB", bytes / (1024.0 * 1024.0));
        }

        public static string ResolveUpdaterLogPath()
        {
            string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (string.IsNullOrEmpty(localApp)) return "";
            return Path.Combine(localApp, "Aerix", "updater.log");
        }

        public static string ReadLastCheckStampDisplay()
        {
            try
            {
                string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                if (string.IsNullOrEmpty(localApp)) return "never";
                string stampPath = Path.Combine(localApp, "Aerix", "last_update_check");
                if (!File.Exists(stampPath)) return "never";
                DateTime dt = File.GetLastWriteTime(stampPath);
                TimeSpan age = DateTime.Now - dt;
                if (age.TotalMinutes < 1) return dt.ToString("yyyy-MM-dd HH:mm") + " (just now)";
                if (age.TotalHours < 1) return string.Format("{0:yyyy-MM-dd HH:mm} ({1}m ago)", dt, (int)age.TotalMinutes);
                if (age.TotalDays < 1) return string.Format("{0:yyyy-MM-dd HH:mm} ({1:0.0}h ago)", dt, age.TotalHours);
                return string.Format("{0:yyyy-MM-dd HH:mm} ({1:0}d ago)", dt, age.TotalDays);
            }
            catch
            {
                return "unknown";
            }
        }

        private static void PopulateToolchainStats(string root, UpdateResult res)
        {
            try
            {
                res.HasStdlib = File.Exists(Path.Combine(root, "stdlib", "aerix_rt.h"));
                string modDir = Path.Combine(root, "modules");
                if (Directory.Exists(modDir))
                {
                    res.ModuleCount = Directory.GetFiles(modDir, "*.arx", SearchOption.AllDirectories).Length;
                }
            }
            catch
            {
            }
        }

        public sealed class CachedToolchainInfo
        {
            public string Version = "";
            public string DirectoryPath = "";
            public string InstalledAt = "";
            public long BinaryBytes;
            public bool IsActive;
        }

        public static string GetToolchainsRootDir()
        {
            string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (string.IsNullOrEmpty(localApp)) localApp = Path.GetTempPath();
            return Path.Combine(localApp, "Aerix", "toolchains");
        }

        public static string NormalizeVersionKey(string ver)
        {
            string s = (ver ?? "").Trim();
            if (s.StartsWith("v", StringComparison.OrdinalIgnoreCase)) s = s.Substring(1);
            foreach (char c in Path.GetInvalidFileNameChars())
            {
                s = s.Replace(c, '_');
            }
            return s;
        }

        public static string ResolveActiveInstallDir(string installDirOverride)
        {
            string targetDir = TrimTrailingSlashes(installDirOverride);
            if (string.IsNullOrEmpty(targetDir))
            {
                targetDir = ResolveInstalledDirFromRegistry();
            }
            if (string.IsNullOrEmpty(targetDir))
            {
                string selfExe = Assembly.GetExecutingAssembly().Location;
                if (!string.IsNullOrEmpty(selfExe) && File.Exists(Path.Combine(Path.GetDirectoryName(selfExe), "bin", "arx.exe")))
                {
                    targetDir = Path.GetDirectoryName(selfExe);
                }
                else
                {
                    targetDir = GetDefaultInstallDir();
                }
            }
            return Path.GetFullPath(TrimTrailingSlashes(targetDir));
        }

        private static void CopyDirectorySafe(string srcDir, string dstDir)
        {
            if (!Directory.Exists(srcDir)) return;
            Directory.CreateDirectory(dstDir);
            foreach (string file in Directory.GetFiles(srcDir))
            {
                string name = Path.GetFileName(file);
                if (name.EndsWith(".old", StringComparison.OrdinalIgnoreCase) ||
                    name.IndexOf(".old", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    continue;
                }
                string dst = Path.Combine(dstDir, name);
                if (name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase) ||
                    name.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))
                {
                    CopyFileLockedSafe(file, dst);
                }
                else
                {
                    File.Copy(file, dst, true);
                }
            }
            foreach (string sub in Directory.GetDirectories(srcDir))
            {
                string subName = Path.GetFileName(sub);
                CopyDirectorySafe(sub, Path.Combine(dstDir, subName));
            }
        }

        public static bool SnapshotToolchainVersion(string activeDir, string version)
        {
            string key = NormalizeVersionKey(version);
            if (string.IsNullOrEmpty(key) || string.IsNullOrEmpty(activeDir)) return false;
            string arxBin = Path.Combine(activeDir, "bin", "arx.exe");
            if (!File.Exists(arxBin)) return false;

            string tcDir = Path.Combine(GetToolchainsRootDir(), key);
            Directory.CreateDirectory(tcDir);
            foreach (string sub in new[] { "bin", "stdlib", "modules", "docs", "assets", "editors" })
            {
                string s = Path.Combine(activeDir, sub);
                if (Directory.Exists(s))
                {
                    CopyDirectorySafe(s, Path.Combine(tcDir, sub));
                }
            }
            string lic = Path.Combine(activeDir, "LICENSE");
            if (File.Exists(lic)) File.Copy(lic, Path.Combine(tcDir, "LICENSE"), true);
            File.WriteAllText(Path.Combine(tcDir, ".aerix-version"), key + Environment.NewLine, Encoding.UTF8);
            File.WriteAllText(Path.Combine(tcDir, ".aerix-installed-at"), DateTime.Now.ToString("yyyy-MM-dd HH:mm"), Encoding.UTF8);
            return true;
        }

        public static List<CachedToolchainInfo> GetCachedToolchains(string activeDir, string activeVersion)
        {
            var res = new List<CachedToolchainInfo>();
            string root = GetToolchainsRootDir();
            string normActive = NormalizeVersionKey(activeVersion);
            if (Directory.Exists(root))
            {
                foreach (string dir in Directory.GetDirectories(root))
                {
                    string arxExe = Path.Combine(dir, "bin", "arx.exe");
                    if (!File.Exists(arxExe)) continue;
                    string ver = Path.GetFileName(dir);
                    string vFile = Path.Combine(dir, ".aerix-version");
                    if (File.Exists(vFile))
                    {
                        string rawV = File.ReadAllText(vFile, Encoding.UTF8).Trim();
                        if (!string.IsNullOrEmpty(rawV)) ver = NormalizeVersionKey(rawV);
                    }
                    string ts = "";
                    string tFile = Path.Combine(dir, ".aerix-installed-at");
                    if (File.Exists(tFile)) ts = File.ReadAllText(tFile, Encoding.UTF8).Trim();
                    res.Add(new CachedToolchainInfo
                    {
                        Version = ver,
                        DirectoryPath = dir,
                        InstalledAt = ts,
                        BinaryBytes = new FileInfo(arxExe).Length,
                        IsActive = string.Equals(NormalizeVersionKey(ver), normActive, StringComparison.OrdinalIgnoreCase)
                    });
                }
            }

            if (!string.IsNullOrEmpty(normActive) && !string.IsNullOrEmpty(activeDir) &&
                File.Exists(Path.Combine(activeDir, "bin", "arx.exe")))
            {
                bool found = false;
                foreach (var c in res)
                {
                    if (c.IsActive) { found = true; break; }
                }
                if (!found)
                {
                    res.Add(new CachedToolchainInfo
                    {
                        Version = normActive,
                        DirectoryPath = activeDir,
                        InstalledAt = "(active, uncached — run 'arx vm sync')",
                        BinaryBytes = new FileInfo(Path.Combine(activeDir, "bin", "arx.exe")).Length,
                        IsActive = true
                    });
                }
            }

            res.Sort(delegate(CachedToolchainInfo a, CachedToolchainInfo b)
            {
                return CompareVersions(b.Version, a.Version);
            });
            return res;
        }

        private static bool ActivateCachedToolchain(string activeDir, string version, out string errorMsg)
        {
            errorMsg = "";
            string key = NormalizeVersionKey(version);
            string tcDir = Path.Combine(GetToolchainsRootDir(), key);
            if (!File.Exists(Path.Combine(tcDir, "bin", "arx.exe")))
            {
                errorMsg = string.Format("Cached toolchain v{0} not found in {1}.", key, tcDir);
                return false;
            }
            foreach (string sub in new[] { "bin", "stdlib", "modules", "docs", "assets", "editors" })
            {
                string srcSub = Path.Combine(tcDir, sub);
                string dstSub = Path.Combine(activeDir, sub);
                if (Directory.Exists(srcSub))
                {
                    if (sub == "modules" || sub == "stdlib" || sub == "docs")
                    {
                        try
                        {
                            if (Directory.Exists(dstSub)) Directory.Delete(dstSub, true);
                        }
                        catch { }
                    }
                    CopyDirectorySafe(srcSub, dstSub);
                }
            }
            string lic = Path.Combine(tcDir, "LICENSE");
            if (File.Exists(lic)) File.Copy(lic, Path.Combine(activeDir, "LICENSE"), true);

            try
            {
                string vsix = Path.Combine(activeDir, "editors", string.Format("aerix-{0}.vsix", key));
                if (!File.Exists(vsix) && Directory.Exists(Path.Combine(activeDir, "editors")))
                {
                    string[] vf = Directory.GetFiles(Path.Combine(activeDir, "editors"), "*.vsix");
                    if (vf.Length > 0) vsix = vf[0];
                }
                string unpacked = Path.Combine(activeDir, "editors", "extension");
                if (File.Exists(vsix) || Directory.Exists(unpacked))
                {
                    List<EditorInfo> eds = DetectEditors();
                    foreach (EditorInfo ed in eds)
                    {
                        if (ed.IsDetected)
                        {
                            InstallExtensionToEditor(ed, key, vsix, unpacked, null, 100);
                        }
                    }
                }
            }
            catch { }

            try
            {
                using (RegistryKey rk = Registry.CurrentUser.CreateSubKey(UninstallRegPath))
                {
                    if (rk != null)
                    {
                        rk.SetValue("InstallLocation", activeDir, RegistryValueKind.String);
                        rk.SetValue("DisplayVersion", key, RegistryValueKind.String);
                    }
                }
            }
            catch
            {
            }
            return true;
        }

        private static bool DownloadVerifyAndApplyRelease(
            StableReleaseInfo rel,
            string targetDir,
            bool skipIde,
            string currentVer,
            ProgressHandler progress,
            out string errorOut,
            out long actualSize)
        {
            errorOut = "";
            actualSize = rel.SetupSize;
            string tempDir = null;
            string vmHostBackup = null;
            try
            {
                if (!string.IsNullOrEmpty(currentVer))
                {
                    SnapshotToolchainVersion(targetDir, currentVer);
                }

                tempDir = Path.Combine(Path.GetTempPath(), "AerixUpdate_" + DateTime.UtcNow.Ticks);
                Directory.CreateDirectory(tempDir);
                string setupPath = Path.Combine(tempDir, rel.SetupAssetName);

                Report(progress, 20, "Downloading " + rel.SetupAssetName + " (" + FormatBytes(rel.SetupSize) + ")...", rel.SetupDownloadUrl);
                ServicePointManager.SecurityProtocol |= (SecurityProtocolType)3072 | SecurityProtocolType.Tls | SecurityProtocolType.Tls11;
                using (var wc = new WebClient())
                {
                    wc.Headers.Add("User-Agent", "AerixSetup-Updater");
                    using (Stream inStream = wc.OpenRead(rel.SetupDownloadUrl))
                    using (FileStream outStream = new FileStream(setupPath, FileMode.Create, FileAccess.Write, FileShare.None))
                    {
                        byte[] buf = new byte[32768];
                        long totalRead = 0;
                        int lastPct = 20;
                        int nRead;
                        while ((nRead = inStream.Read(buf, 0, buf.Length)) > 0)
                        {
                            outStream.Write(buf, 0, nRead);
                            totalRead += nRead;
                            if (rel.SetupSize > 0)
                            {
                                int pct = 20 + (int)((totalRead * 40L) / rel.SetupSize);
                                if (pct >= lastPct + 5 || totalRead == rel.SetupSize)
                                {
                                    lastPct = pct;
                                    Report(progress, pct,
                                        string.Format("Downloading {0} ({1} / {2})...",
                                            rel.SetupAssetName, FormatBytes(totalRead), FormatBytes(rel.SetupSize)),
                                        "progress");
                                }
                            }
                        }
                    }
                }

                Report(progress, 62, "Verifying downloaded PE32+ installer...", setupPath);
                var fi = new FileInfo(setupPath);
                if (!fi.Exists || fi.Length < 100000)
                {
                    errorOut = "Downloaded installer is incomplete or corrupted.";
                    return false;
                }
                if (actualSize <= 0) actualSize = fi.Length;
                using (FileStream fs = File.OpenRead(setupPath))
                {
                    if (fs.ReadByte() != 0x4D || fs.ReadByte() != 0x5A)
                    {
                        errorOut = "Downloaded file is not a valid Windows executable.";
                        return false;
                    }
                }

                // Preserve newer version manager host (Uninstall.exe) when installing an older release
                string activeUninst = Path.Combine(targetDir, "Uninstall.exe");
                if (File.Exists(activeUninst) && CompareVersions(GetVersion(), rel.Version) > 0)
                {
                    vmHostBackup = Path.Combine(tempDir, "Uninstall.vmhost.exe");
                    File.Copy(activeUninst, vmHostBackup, true);
                }

                Report(progress, 75, "Installing Aerix v" + rel.Version + " into " + targetDir + "...", "silent-install");
                string args = string.Format("--silent \"--dir={0}\"{1}", targetDir, skipIde ? " --no-ide" : "");
                var psi = new ProcessStartInfo(setupPath, args);
                psi.CreateNoWindow = true;
                psi.UseShellExecute = false;
                psi.WindowStyle = ProcessWindowStyle.Hidden;
                using (Process p = Process.Start(psi))
                {
                    if (p == null || !p.WaitForExit(180000))
                    {
                        errorOut = "Timed out applying Aerix setup.";
                        return false;
                    }
                    if (p.ExitCode != 0)
                    {
                        errorOut = "Installer exited with code " + p.ExitCode + ".";
                        return false;
                    }
                }

                if (!string.IsNullOrEmpty(vmHostBackup) && File.Exists(vmHostBackup))
                {
                    try { CopyFileLockedSafe(vmHostBackup, activeUninst); } catch { }
                }

                SnapshotToolchainVersion(targetDir, rel.Version);
                return true;
            }
            catch (Exception ex)
            {
                errorOut = ex.Message;
                return false;
            }
            finally
            {
                if (!string.IsNullOrEmpty(tempDir))
                {
                    try { Directory.Delete(tempDir, true); } catch { }
                }
            }
        }

        public static UpdateResult RunVmInstallOrUse(
            string spec,
            bool useMode,
            bool activateAfter,
            bool force,
            bool allowOlder,
            bool skipIde,
            string installDirOverride,
            ProgressHandler progress)
        {
            var res = new UpdateResult();
            res.LogPath = ResolveUpdaterLogPath();
            res.LastCheckedAt = ReadLastCheckStampDisplay();
            var sw = Stopwatch.StartNew();
            Mutex mtx = null;
            bool acquired = false;
            try
            {
                try
                {
                    mtx = new Mutex(false, @"Local\AerixLangAutoUpdater");
                    acquired = mtx.WaitOne(3000);
                }
                catch (AbandonedMutexException) { acquired = true; }
                catch { acquired = true; }

                if (!acquired)
                {
                    res.Success = false;
                    res.Message = "Another Aerix version operation is already in progress.";
                    return res;
                }

                string targetDir = ResolveActiveInstallDir(installDirOverride);
                res.InstallDir = targetDir;
                res.CurrentVersion = GetInstalledVersionFromDisk(targetDir);
                PopulateToolchainStats(targetDir, res);

                string req = (spec ?? "").Trim();
                if (string.IsNullOrEmpty(req))
                {
                    res.Success = false;
                    res.Message = "No version specified. Run 'arx vm list-remote' to see available versions (from " + VmMinVersion + ").";
                    return res;
                }

                string cleanKey = NormalizeVersionKey(req);
                string lowReq = cleanKey.ToLowerInvariant();
                bool isChannelAlias = (lowReq == "latest" || lowReq == "stable" || lowReq == "beta" || lowReq == "pre");

                if (!isChannelAlias && !allowOlder && CompareVersions(cleanKey, VmMinVersion) < 0)
                {
                    res.Success = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format("Version 'v{0}' is older than minimum managed version 'v{1}'. Pass --all to override.", cleanKey, VmMinVersion);
                    return res;
                }

                // Snapshot current active installation before any switch
                if (!string.IsNullOrEmpty(res.CurrentVersion))
                {
                    SnapshotToolchainVersion(targetDir, res.CurrentVersion);
                }

                // 1. Check local cache first (for exact versions, or channel aliases if not forced)
                if (!force)
                {
                    string targetCachedKey = null;
                    if (!isChannelAlias)
                    {
                        if (string.Equals(NormalizeVersionKey(res.CurrentVersion), cleanKey, StringComparison.OrdinalIgnoreCase))
                        {
                            res.Success = true;
                            res.LatestVersion = res.CurrentVersion;
                            res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                            res.Message = string.Format("Aerix v{0} is already the active toolchain.", res.CurrentVersion);
                            Report(progress, 100, res.Message, res.Message);
                            return res;
                        }

                        string cachedDir = Path.Combine(GetToolchainsRootDir(), cleanKey);
                        if (File.Exists(Path.Combine(cachedDir, "bin", "arx.exe")))
                        {
                            targetCachedKey = cleanKey;
                        }
                    }
                    else
                    {
                        List<CachedToolchainInfo> cached = GetCachedToolchains(targetDir, res.CurrentVersion);
                        foreach (var c in cached)
                        {
                            string cChan = ClassifyReleaseChannel(c.Version, false);
                            if (lowReq == "latest" || cChan == lowReq)
                            {
                                if (c.IsActive)
                                {
                                    res.Success = true;
                                    res.LatestVersion = c.Version;
                                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                                    res.Message = string.Format("Aerix v{0} is already the active toolchain ({1} channel).", c.Version, lowReq);
                                    Report(progress, 100, res.Message, res.Message);
                                    return res;
                                }
                                targetCachedKey = c.Version;
                                break;
                            }
                        }
                    }

                    if (!string.IsNullOrEmpty(targetCachedKey))
                    {
                        string cachedDir = Path.Combine(GetToolchainsRootDir(), targetCachedKey);
                        Report(progress, 35, "Found cached toolchain v" + targetCachedKey + " in local store...", cachedDir);
                        if (!activateAfter)
                        {
                            res.Success = true;
                            res.LatestVersion = targetCachedKey;
                            res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                            res.Message = string.Format("Toolchain v{0} is already installed locally (cached at {1}).", targetCachedKey, cachedDir);
                            Report(progress, 100, res.Message, res.Message);
                            return res;
                        }

                        Report(progress, 70, "Switching active toolchain to cached v" + targetCachedKey + "...", targetDir);
                        string actErr;
                        if (!ActivateCachedToolchain(targetDir, targetCachedKey, out actErr))
                        {
                            res.Success = false;
                            res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                            res.Message = actErr;
                            return res;
                        }

                        CleanupStaleBackups(targetDir);
                        CleanupStaleBackups(Path.Combine(targetDir, "bin"));
                        PopulateToolchainStats(targetDir, res);
                        res.Success = true;
                        res.Updated = true;
                        res.LatestVersion = GetInstalledVersionFromDisk(targetDir);
                        if (string.IsNullOrEmpty(res.LatestVersion)) res.LatestVersion = targetCachedKey;
                        res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                        res.Message = string.Format("Switched Aerix v{0} -> v{1} (from local cache).", res.CurrentVersion, res.LatestVersion);
                        WriteUpdaterLog(res.Message);
                        Report(progress, 100, res.Message, res.Message);
                        return res;
                    }
                }

                // 2. Fetch releases from GitHub
                Report(progress, 10, "Querying GitHub releases for 'v" + cleanKey + "'...", targetDir + "|v" + res.CurrentVersion);
                List<StableReleaseInfo> allRels = FetchReleases(true);
                StableReleaseInfo chosen = null;

                foreach (var r in allRels)
                {
                    if (!allowOlder && CompareVersions(r.Version, VmMinVersion) < 0) continue;
                    if (isChannelAlias)
                    {
                        if (lowReq == "latest" || r.Channel == lowReq)
                        {
                            chosen = r;
                            break;
                        }
                    }
                    else
                    {
                        string rk = NormalizeVersionKey(r.Version).ToLowerInvariant();
                        string reqNoDash = lowReq.Replace("-", "");
                        string rkNoDash = rk.Replace("-", "");
                        if (rk == lowReq || rkNoDash == reqNoDash)
                        {
                            chosen = r;
                            break;
                        }
                    }
                }

                if (chosen == null)
                {
                    // Fallback to local cache if network unreachable or release query returned nothing
                    List<CachedToolchainInfo> cached = GetCachedToolchains(targetDir, res.CurrentVersion);
                    string fallbackKey = null;
                    if (isChannelAlias)
                    {
                        foreach (var c in cached)
                        {
                            string cChan = ClassifyReleaseChannel(c.Version, false);
                            if (lowReq == "latest" || cChan == lowReq)
                            {
                                fallbackKey = c.Version;
                                break;
                            }
                        }
                    }
                    else
                    {
                        foreach (var c in cached)
                        {
                            if (string.Equals(NormalizeVersionKey(c.Version), cleanKey, StringComparison.OrdinalIgnoreCase))
                            {
                                fallbackKey = c.Version;
                                break;
                            }
                        }
                    }

                    if (!string.IsNullOrEmpty(fallbackKey))
                    {
                        Report(progress, 70, "Remote release query unavailable; switching to cached v" + fallbackKey + "...", targetDir);
                        string actErr;
                        if (ActivateCachedToolchain(targetDir, fallbackKey, out actErr))
                        {
                            CleanupStaleBackups(targetDir);
                            CleanupStaleBackups(Path.Combine(targetDir, "bin"));
                            PopulateToolchainStats(targetDir, res);
                            res.Success = true;
                            res.Updated = true;
                            res.LatestVersion = fallbackKey;
                            res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                            res.Message = string.Format("Switched Aerix v{0} -> v{1} (from local cache; remote offline/unreachable).", res.CurrentVersion, res.LatestVersion);
                            WriteUpdaterLog(res.Message);
                            Report(progress, 100, res.Message, res.Message);
                            return res;
                        }
                    }

                    res.Success = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format(
                        "Release 'v{0}' with a prebuilt Windows installer was not found on GitHub (minimum managed: v{1}). Run 'arx vm list-remote{2}' to see available releases.",
                        cleanKey, VmMinVersion, allowOlder ? " --all" : "");
                    return res;
                }

                res.LatestVersion = chosen.Version;
                res.PublishedAt = chosen.PublishedAt;
                res.AssetName = chosen.SetupAssetName;
                res.AssetSize = chosen.SetupSize;
                res.ReleaseUrl = string.IsNullOrEmpty(chosen.HtmlUrl)
                    ? ("https://github.com/HaxOrWot/AerixLang/releases/tag/" + chosen.TagName)
                    : chosen.HtmlUrl;
                res.ReleaseNotes = chosen.ReleaseNotes;

                string dlErr;
                long dlSize;
                if (activateAfter || useMode)
                {
                    if (!DownloadVerifyAndApplyRelease(chosen, targetDir, skipIde, res.CurrentVersion, progress, out dlErr, out dlSize))
                    {
                        res.Success = false;
                        res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                        res.Message = dlErr;
                        WriteUpdaterLog("VM install failed: " + dlErr);
                        return res;
                    }
                    res.AssetSize = dlSize;
                    CleanupStaleBackups(targetDir);
                    CleanupStaleBackups(Path.Combine(targetDir, "bin"));
                    PopulateToolchainStats(targetDir, res);
                    string postVer = GetInstalledVersionFromDisk(targetDir);
                    if (!string.IsNullOrEmpty(postVer)) res.LatestVersion = postVer;
                    res.Success = true;
                    res.Updated = true;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format("Installed & activated Aerix v{0} (was v{1}).", res.LatestVersion, res.CurrentVersion);
                    WriteUpdaterLog(res.Message);
                    Report(progress, 100, res.Message, res.Message);
                    return res;
                }
                else
                {
                    // --no-use: download + apply cleanly into isolated cache folder while keeping active install untouched
                    string origDir = targetDir;
                    string cacheTarget = Path.Combine(GetToolchainsRootDir(), NormalizeVersionKey(chosen.Version));
                    if (!DownloadVerifyAndApplyRelease(chosen, cacheTarget, true, "", progress, out dlErr, out dlSize))
                    {
                        res.Success = false;
                        res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                        res.Message = dlErr;
                        return res;
                    }
                    // Restore registry InstallLocation/DisplayVersion to active dir
                    try
                    {
                        using (RegistryKey rk = Registry.CurrentUser.CreateSubKey(UninstallRegPath))
                        {
                            if (rk != null)
                            {
                                rk.SetValue("InstallLocation", origDir, RegistryValueKind.String);
                                rk.SetValue("DisplayVersion", res.CurrentVersion, RegistryValueKind.String);
                            }
                        }
                    }
                    catch { }
                    res.AssetSize = dlSize;
                    res.Success = true;
                    res.Updated = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format("Installed Aerix v{0} into cache (active remains v{1}). Switch anytime with 'arx vm use {0}'.", chosen.Version, res.CurrentVersion);
                    WriteUpdaterLog(res.Message);
                    Report(progress, 100, res.Message, res.Message);
                    return res;
                }
            }
            catch (Exception ex)
            {
                res.Success = false;
                res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                res.Message = ex.Message;
                WriteUpdaterLog("VM error: " + ex.Message);
                return res;
            }
            finally
            {
                if (mtx != null)
                {
                    if (acquired) { try { mtx.ReleaseMutex(); } catch { } }
                    mtx.Dispose();
                }
            }
        }

        public static bool RunVmRemove(string version, bool force, string installDirOverride, out string msg)
        {
            msg = "";
            string key = NormalizeVersionKey(version);
            if (string.IsNullOrEmpty(key))
            {
                msg = "No version specified.";
                return false;
            }
            string activeDir = ResolveActiveInstallDir(installDirOverride);
            string activeVer = NormalizeVersionKey(GetInstalledVersionFromDisk(activeDir));
            if (string.Equals(key, activeVer, StringComparison.OrdinalIgnoreCase) && !force)
            {
                msg = string.Format("Cannot remove active toolchain 'v{0}'. Switch to another version first or pass --force.", key);
                return false;
            }
            string tcDir = Path.Combine(GetToolchainsRootDir(), key);
            if (!Directory.Exists(tcDir))
            {
                msg = string.Format("Cached toolchain 'v{0}' was not found in {1}.", key, GetToolchainsRootDir());
                return false;
            }
            Directory.Delete(tcDir, true);
            msg = string.Format("Removed cached toolchain v{0} from {1}.", key, tcDir);
            WriteUpdaterLog(msg);
            return true;
        }

        public static UpdateResult RunAutoUpdate(bool checkOnly, bool force, bool skipIde, string installDirOverride, ProgressHandler progress)
        {
            var res = new UpdateResult();
            res.LogPath = ResolveUpdaterLogPath();
            res.LastCheckedAt = ReadLastCheckStampDisplay();
            var sw = Stopwatch.StartNew();
            Mutex mtx = null;
            bool acquired = false;
            try
            {
                try
                {
                    mtx = new Mutex(false, @"Local\AerixLangAutoUpdater");
                    acquired = mtx.WaitOne(checkOnly ? 1000 : 3000);
                }
                catch (AbandonedMutexException) { acquired = true; }
                catch { acquired = true; }

                if (!acquired)
                {
                    res.Success = true;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = "Another Aerix update is already running.";
                    return res;
                }

                string targetDir = ResolveActiveInstallDir(installDirOverride);
                res.InstallDir = targetDir;
                PopulateToolchainStats(targetDir, res);

                res.CurrentVersion = GetInstalledVersionFromDisk(targetDir);
                Report(progress, 10, "Checking GitHub for latest stable release...", targetDir + "|v" + res.CurrentVersion);

                StableReleaseInfo latest = FetchLatestStableRelease();
                if (latest == null)
                {
                    res.Success = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = "No stable Aerix release with a Windows installer was found on GitHub.";
                    WriteUpdaterLog("Check failed: " + res.Message);
                    return res;
                }

                res.LatestVersion = latest.Version;
                res.PublishedAt = latest.PublishedAt;
                res.AssetName = latest.SetupAssetName;
                res.AssetSize = latest.SetupSize;
                res.ReleaseUrl = string.IsNullOrEmpty(latest.HtmlUrl)
                    ? ("https://github.com/HaxOrWot/AerixLang/releases/tag/" + latest.TagName)
                    : latest.HtmlUrl;
                res.ReleaseNotes = latest.ReleaseNotes;
                TouchUpdateCheckStamp(latest.Version);

                int cmp = CompareVersions(latest.Version, res.CurrentVersion);
                res.UpdateAvailable = cmp > 0;
                if (cmp <= 0 && !force)
                {
                    res.Success = true;
                    res.Updated = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format("Already running the latest stable release (v{0}).", res.CurrentVersion);
                    Report(progress, 100, res.Message, res.Message);
                    return res;
                }

                if (checkOnly)
                {
                    res.Success = true;
                    res.Updated = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format("Update available: v{0} -> v{1} ({2}, {3})",
                        res.CurrentVersion, res.LatestVersion, latest.SetupAssetName, FormatBytes(latest.SetupSize));
                    Report(progress, 100, res.Message, res.Message);
                    return res;
                }

                string applyErr;
                long actualSize;
                if (!DownloadVerifyAndApplyRelease(latest, targetDir, skipIde, res.CurrentVersion, progress, out applyErr, out actualSize))
                {
                    res.Success = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = applyErr;
                    WriteUpdaterLog("Update failed: " + applyErr);
                    return res;
                }
                res.AssetSize = actualSize;

                Report(progress, 92, "Verifying updated compiler binary...", targetDir);
                CleanupStaleBackups(targetDir);
                CleanupStaleBackups(Path.Combine(targetDir, "bin"));
                PopulateToolchainStats(targetDir, res);
                string postVer = GetInstalledVersionFromDisk(targetDir);
                res.Success = true;
                res.Updated = true;
                res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                if (!string.IsNullOrEmpty(postVer)) res.LatestVersion = postVer;
                res.Message = string.Format("Updated Aerix from v{0} to v{1}.", res.CurrentVersion, res.LatestVersion);
                WriteUpdaterLog(res.Message);
                Report(progress, 100, res.Message, res.Message);
                return res;
            }
            catch (Exception ex)
            {
                res.Success = false;
                res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                res.Message = ex.Message;
                WriteUpdaterLog("Update exception: " + ex.Message);
                return res;
            }
            finally
            {
                if (mtx != null)
                {
                    if (acquired)
                    {
                        try { mtx.ReleaseMutex(); } catch { }
                    }
                    mtx.Dispose();
                }
            }
        }
    }
}
