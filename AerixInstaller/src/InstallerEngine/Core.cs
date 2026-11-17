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
        public const string DefaultVersion = "3.0.0-beta.4";
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


    }
}
