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
                if (!string.IsNullOrEmpty(selfExe))
                {
                    string dir = Path.GetDirectoryName(selfExe);
                    if (File.Exists(Path.Combine(dir, "bin", "arx.exe")))
                    {
                        targetDir = dir;
                    }
                    else if (File.Exists(Path.Combine(dir, "arx.exe")) && string.Equals(Path.GetFileName(dir), "bin", StringComparison.OrdinalIgnoreCase))
                    {
                        targetDir = Path.GetDirectoryName(dir);
                    }
                }
                if (string.IsNullOrEmpty(targetDir))
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

                // Preserve newer version manager host (Uninstall.exe & Updater.exe) when installing an older release
                string activeUninst = Path.Combine(targetDir, "Uninstall.exe");
                if (File.Exists(activeUninst) && CompareVersions(GetVersion(), rel.Version) > 0)
                {
                    vmHostBackup = Path.Combine(tempDir, "Uninstall.vmhost.exe");
                    File.Copy(activeUninst, vmHostBackup, true);
                }
                string activeUpdater = Path.Combine(targetDir, "Updater.exe");
                string updaterBackup = null;
                if (File.Exists(activeUpdater) && CompareVersions(GetVersion(), rel.Version) > 0)
                {
                    updaterBackup = Path.Combine(tempDir, "Updater.vmhost.exe");
                    File.Copy(activeUpdater, updaterBackup, true);
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
                if (!string.IsNullOrEmpty(updaterBackup) && File.Exists(updaterBackup))
                {
                    try { CopyFileLockedSafe(updaterBackup, activeUpdater); } catch { }
                    try { CopyFileLockedSafe(updaterBackup, Path.Combine(targetDir, "bin", "Updater.exe")); } catch { }
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


    }
}
