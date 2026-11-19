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
    public static partial class InstallerEngine
    {
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
                TerminateRunningAerixProcesses(root);

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

                // 2. Grant modify permissions to Users on the install folder so auto-updates succeed without extra prompts
                GrantDirectoryPermissions(root);

                // 3. Copy self as Uninstall.exe
                Report(progress, 65, "Creating Windows uninstaller...", "Creating Uninstall.exe");
                string selfExe = Assembly.GetExecutingAssembly().Location;
                string uninstExe = Path.Combine(root, "Uninstall.exe");
                if (!string.IsNullOrEmpty(selfExe) && File.Exists(selfExe))
                {
                    if (!string.Equals(Path.GetFullPath(selfExe), Path.GetFullPath(uninstExe), StringComparison.OrdinalIgnoreCase))
                    {
                        CopyFileLockedSafe(selfExe, uninstExe);
                    }
                }
                string updaterExe = Path.Combine(root, "Updater.exe");
                string binUpdaterExe = Path.Combine(root, "bin", "Updater.exe");
                if (!File.Exists(updaterExe) && !string.IsNullOrEmpty(selfExe) && File.Exists(selfExe))
                {
                    CopyFileLockedSafe(selfExe, updaterExe);
                }
                if (!File.Exists(binUpdaterExe) && File.Exists(updaterExe))
                {
                    CopyFileLockedSafe(updaterExe, binUpdaterExe);
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

        public static void TerminateRunningAerixProcesses(string root)
        {
            try
            {
                int currentPid = Process.GetCurrentProcess().Id;
                string normalizedRoot = string.IsNullOrEmpty(root) ? "" : Path.GetFullPath(TrimTrailingSlashes(root)).TrimEnd('\\');

                // 1. Terminate any running process by known Aerix binary names
                string[] targetNames = new[] { "arx", "arxc" };
                foreach (string name in targetNames)
                {
                    try
                    {
                        Process[] procs = Process.GetProcessesByName(name);
                        foreach (Process p in procs)
                        {
                            try
                            {
                                if (p.Id != currentPid)
                                {
                                    p.Kill();
                                    p.WaitForExit(1500);
                                }
                            }
                            catch { }
                            finally
                            {
                                p.Dispose();
                            }
                        }
                    }
                    catch { }
                }

                // 2. Terminate any process whose executable path is located inside the root directory
                if (!string.IsNullOrEmpty(normalizedRoot) && Directory.Exists(normalizedRoot))
                {
                    try
                    {
                        Process[] all = Process.GetProcesses();
                        foreach (Process p in all)
                        {
                            try
                            {
                                if (p.Id == currentPid) continue;
                                string modPath = null;
                                try
                                {
                                    if (p.MainModule != null)
                                    {
                                        modPath = p.MainModule.FileName;
                                    }
                                }
                                catch
                                {
                                    // Ignore access denied on system / protected processes
                                }

                                if (!string.IsNullOrEmpty(modPath))
                                {
                                    string fullMod = Path.GetFullPath(modPath);
                                    if (fullMod.StartsWith(normalizedRoot + "\\", StringComparison.OrdinalIgnoreCase) ||
                                        string.Equals(fullMod, normalizedRoot, StringComparison.OrdinalIgnoreCase))
                                    {
                                        try
                                        {
                                            p.Kill();
                                            p.WaitForExit(1500);
                                        }
                                        catch { }
                                    }
                                }
                            }
                            catch { }
                            finally
                            {
                                p.Dispose();
                            }
                        }
                    }
                    catch { }
                }

                // 3. Fallback: taskkill force kill tree
                foreach (string img in new[] { "arx.exe", "arxc.exe" })
                {
                    try
                    {
                        var psi = new ProcessStartInfo("taskkill.exe", string.Format("/F /IM {0} /T", img))
                        {
                            CreateNoWindow = true,
                            UseShellExecute = false,
                            WindowStyle = ProcessWindowStyle.Hidden
                        };
                        using (Process tk = Process.Start(psi))
                        {
                            if (tk != null) tk.WaitForExit(2000);
                        }
                    }
                    catch { }
                }

                // Give Windows kernel time to release open file handles
                Thread.Sleep(300);
            }
            catch { }
        }

        public static void ForceDeleteDirectory(string path)
        {
            if (string.IsNullOrEmpty(path) || !Directory.Exists(path)) return;

            string selfExe = Assembly.GetExecutingAssembly().Location;
            string selfNorm = string.IsNullOrEmpty(selfExe) ? "" : Path.GetFullPath(selfExe);

            for (int attempt = 1; attempt <= 3; attempt++)
            {
                try
                {
                    var di = new DirectoryInfo(path);
                    if (!di.Exists) return;

                    foreach (FileInfo fi in di.GetFiles("*", SearchOption.AllDirectories))
                    {
                        try
                        {
                            if (!string.IsNullOrEmpty(selfNorm) &&
                                string.Equals(fi.FullName, selfNorm, StringComparison.OrdinalIgnoreCase))
                            {
                                continue;
                            }
                            if (fi.Attributes != FileAttributes.Normal)
                            {
                                fi.Attributes = FileAttributes.Normal;
                            }
                            fi.Delete();
                        }
                        catch { }
                    }

                    DirectoryInfo[] subDirs = di.GetDirectories("*", SearchOption.AllDirectories);
                    Array.Sort(subDirs, delegate(DirectoryInfo a, DirectoryInfo b)
                    {
                        return b.FullName.Length.CompareTo(a.FullName.Length);
                    });
                    foreach (DirectoryInfo sub in subDirs)
                    {
                        try
                        {
                            if (sub.Attributes != FileAttributes.Normal)
                            {
                                sub.Attributes = FileAttributes.Normal;
                            }
                            sub.Delete(true);
                        }
                        catch { }
                    }

                    if (di.Attributes != FileAttributes.Normal)
                    {
                        di.Attributes = FileAttributes.Normal;
                    }

                    if (string.IsNullOrEmpty(selfNorm) ||
                        (!string.Equals(di.FullName.TrimEnd('\\'), Path.GetDirectoryName(selfNorm).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase) &&
                         !selfNorm.StartsWith(di.FullName.TrimEnd('\\') + "\\", StringComparison.OrdinalIgnoreCase)))
                    {
                        di.Delete(true);
                    }
                    return;
                }
                catch
                {
                    if (attempt < 3)
                    {
                        Thread.Sleep(200);
                    }
                }
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

                Report(progress, 10, "Closing background Aerix processes...", "Stopping active compiler and LSP daemons");
                TerminateRunningAerixProcesses(root);

                Report(progress, 25, "Removing environment variables & PATH...", "Cleaning HKCU\\Environment");

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

                Report(progress, 50, "Removing file associations & registry keys...", "Cleaning HKCU\\Software\\Classes\\.arx");
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

                Report(progress, 75, "Removing installed Aerix files...", "Deleting toolchain directories");
                if (Directory.Exists(root))
                {
                    foreach (string dir in Directory.GetDirectories(root))
                    {
                        ForceDeleteDirectory(dir);
                    }
                }

                string selfExe = Assembly.GetExecutingAssembly().Location;
                string selfNorm = string.IsNullOrEmpty(selfExe) ? "" : Path.GetFullPath(selfExe);
                string selfDir = string.IsNullOrEmpty(selfNorm) ? "" : Path.GetDirectoryName(selfNorm).TrimEnd('\\');
                string normRoot = root.TrimEnd('\\');
                bool isRunningInsideRoot = !string.IsNullOrEmpty(selfDir) &&
                    (string.Equals(selfDir, normRoot, StringComparison.OrdinalIgnoreCase) ||
                     selfDir.StartsWith(normRoot + "\\", StringComparison.OrdinalIgnoreCase));

                if (!isRunningInsideRoot)
                {
                    ForceDeleteDirectory(root);
                }
                else
                {
                    try
                    {
                        if (Directory.Exists(root))
                        {
                            foreach (string f in Directory.GetFiles(root))
                            {
                                if (!string.Equals(Path.GetFullPath(f), selfNorm, StringComparison.OrdinalIgnoreCase))
                                {
                                    try
                                    {
                                        File.SetAttributes(f, FileAttributes.Normal);
                                        File.Delete(f);
                                    }
                                    catch { }
                                }
                            }
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

        public static void GrantDirectoryPermissions(string root)
        {
            try
            {
                if (string.IsNullOrEmpty(root) || !Directory.Exists(root)) return;
                var psi = new ProcessStartInfo("icacls.exe", string.Format("\"{0}\" /grant Users:(OI)(CI)M /T /Q", root));
                psi.CreateNoWindow = true;
                psi.UseShellExecute = false;
                psi.WindowStyle = ProcessWindowStyle.Hidden;
                using (Process p = Process.Start(psi))
                {
                    if (p != null) p.WaitForExit(10000);
                }
            }
            catch { }
        }

        private static bool _selfDeleteScheduled = false;

        public static void ScheduleSelfDeleteIfRunningFrom(string installDir)
        {
            try
            {
                if (_selfDeleteScheduled) return;

                string selfExe = Assembly.GetExecutingAssembly().Location;
                if (string.IsNullOrEmpty(selfExe) || string.IsNullOrWhiteSpace(installDir)) return;
                string selfDir = Path.GetFullPath(Path.GetDirectoryName(selfExe)).TrimEnd('\\');
                string root = Path.GetFullPath(TrimTrailingSlashes(installDir)).TrimEnd('\\');

                bool isInsideRoot = string.Equals(selfDir, root, StringComparison.OrdinalIgnoreCase) ||
                                    selfDir.StartsWith(root + "\\", StringComparison.OrdinalIgnoreCase);
                if (!isInsideRoot) return;

                _selfDeleteScheduled = true;

                try
                {
                    Directory.SetCurrentDirectory(Path.GetTempPath());
                }
                catch { }

                string args = string.Format(
                    "/C ping 127.0.0.1 -n 3 > nul & del /f /q \"{0}\" 2>nul & rmdir /s /q \"{1}\" 2>nul & if exist \"{1}\" (ping 127.0.0.1 -n 2 > nul & rmdir /s /q \"{1}\" 2>nul)",
                    selfExe, root);

                var psi = new ProcessStartInfo("cmd.exe", args)
                {
                    WorkingDirectory = Path.GetTempPath(),
                    CreateNoWindow = true,
                    UseShellExecute = false,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
                Process.Start(psi);
            }
            catch
            {
            }
        }


    }
}
