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
        private static void RegisterFileAssociations(string root)
        {
            string fileIco = Path.Combine(root, "assets", "aerix.ico");
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


    }
}
