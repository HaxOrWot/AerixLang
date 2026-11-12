using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace AerixSetup
{
    internal static class Program
    {
        [DllImport("kernel32.dll")]
        private static extern bool AttachConsole(int dwProcessId);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr GetStdHandle(int nStdHandle);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetConsoleMode(IntPtr hConsoleHandle, out uint lpMode);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetConsoleMode(IntPtr hConsoleHandle, uint dwMode);

        private static bool TryEnableAnsiColor()
        {
            if (Console.IsOutputRedirected) return false;
            if (!string.IsNullOrEmpty(Environment.GetEnvironmentVariable("NO_COLOR"))) return false;
            try
            {
                IntPtr hOut = GetStdHandle(-11);
                if (hOut == IntPtr.Zero || hOut == new IntPtr(-1)) return false;
                uint mode;
                if (!GetConsoleMode(hOut, out mode)) return false;
                if ((mode & 0x0004u) != 0) return true;
                return SetConsoleMode(hOut, mode | 0x0004u);
            }
            catch
            {
                return false;
            }
        }

        private static string FormatPublishedDate(string iso)
        {
            if (string.IsNullOrWhiteSpace(iso)) return "unknown";
            int tIdx = iso.IndexOf('T');
            if (tIdx > 0) return iso.Substring(0, tIdx);
            return iso.Trim();
        }

        [STAThread]
        private static int Main(string[] args)
        {
            bool silent = false;
            bool uninstall = false;
            bool updateMode = false;
            bool checkUpdateOnly = false;
            bool forceUpdate = false;
            bool quietUpdate = false;
            bool verboseUpdate = false;
            var opts = new InstallOptions();

            string selfExe = Assembly.GetExecutingAssembly().Location;
            if (!string.IsNullOrEmpty(selfExe) &&
                string.Equals(Path.GetFileName(selfExe), "Uninstall.exe", StringComparison.OrdinalIgnoreCase))
            {
                uninstall = true;
            }

            if (args != null)
            {
                foreach (string raw in args)
                {
                    if (string.IsNullOrEmpty(raw)) continue;
                    string low = raw.ToLowerInvariant();
                    if (low == "/s" || low == "-s" || low == "--silent" || low == "/silent")
                    {
                        silent = true;
                    }
                    else if (low == "--uninstall" || low == "/uninstall")
                    {
                        uninstall = true;
                    }
                    else if (low == "--update" || low == "/update")
                    {
                        updateMode = true;
                        uninstall = false;
                    }
                    else if (low == "--check-update" || low == "/check-update")
                    {
                        updateMode = true;
                        checkUpdateOnly = true;
                        uninstall = false;
                    }
                    else if (low == "--force" || low == "/force")
                    {
                        forceUpdate = true;
                    }
                    else if (low == "--verbose" || low == "-v" || low == "/verbose")
                    {
                        verboseUpdate = true;
                    }
                    else if (low == "--quiet" || low == "/quiet")
                    {
                        quietUpdate = true;
                    }
                    else if (low.StartsWith("--dir="))
                    {
                        opts.InstallDir = raw.Substring(6).Trim('"');
                    }
                    else if (low == "--no-env" || low == "--no-path")
                    {
                        opts.ConfigureEnv = false;
                    }
                    else if (low == "--no-assoc")
                    {
                        opts.FileAssociations = false;
                    }
                    else if (low == "--no-ide" || low == "--no-vscode" || low == "--no-antigravity")
                    {
                        opts.InstallIdeExtensions = false;
                    }
                    else if (low == "--no-verify")
                    {
                        opts.RunSmokeTest = false;
                    }
                }
            }

            if (updateMode)
            {
                if (!quietUpdate && !Console.IsOutputRedirected) AttachConsole(-1);
                bool color = !quietUpdate && TryEnableAnsiColor();
                string cBold = color ? "\x1b[1m" : "";
                string cCyan = color ? "\x1b[1;36m" : "";
                string cGreen = color ? "\x1b[1;32m" : "";
                string cYellow = color ? "\x1b[1;33m" : "";
                string cRed = color ? "\x1b[1;31m" : "";
                string cDim = color ? "\x1b[2m" : "";
                string cReset = color ? "\x1b[0m" : "";

                if (!quietUpdate)
                {
                    Console.WriteLine(cCyan + "Aerix Toolchain Updater" + cReset + cDim + " (stable channel)" + cReset);
                }

                bool headerPrinted = false;
                UpdateResult res = InstallerEngine.RunAutoUpdate(
                    checkUpdateOnly,
                    forceUpdate,
                    !opts.InstallIdeExtensions,
                    opts.InstallDir,
                    delegate(int pct, string status, string logLine)
                    {
                        if (quietUpdate) return;
                        if (pct == 10 && !headerPrinted && logLine != null && logLine.Contains("|"))
                        {
                            headerPrinted = true;
                            string[] hp = logLine.Split('|');
                            Console.WriteLine("  Install path : {0}", hp[0]);
                            Console.WriteLine("  Installed    : {0}{1}{2}", cBold, hp.Length > 1 ? hp[1] : "", cReset);
                            Console.WriteLine("  Repository   : https://github.com/HaxOrWot/AerixLang/releases");
                            Console.WriteLine();
                        }
                        if (pct < 100)
                        {
                            Console.WriteLine("  {0}[{1,3}%]{2} {3}", cDim, pct, cReset, status);
                        }
                    });

                if (!quietUpdate)
                {
                    Console.WriteLine();
                    if (!res.Success)
                    {
                        Console.Error.WriteLine("{0}error:{1} {2}", cRed, cReset, res.Message);
                        if (!string.IsNullOrEmpty(res.LogPath))
                        {
                            Console.Error.WriteLine("  {0}Log file:{1} {2}", cDim, cReset, res.LogPath);
                        }
                    }
                    else
                    {
                        if (!string.IsNullOrEmpty(res.LatestVersion))
                        {
                            Console.WriteLine("  Latest stable : {0}v{1}{2}  (published {3})",
                                cBold, res.LatestVersion, cReset, FormatPublishedDate(res.PublishedAt));
                        }
                        if (!string.IsNullOrEmpty(res.AssetName))
                        {
                            Console.WriteLine("  Package       : {0} ({1})",
                                res.AssetName, InstallerEngine.FormatBytes(res.AssetSize));
                        }
                        if (!string.IsNullOrEmpty(res.ReleaseUrl))
                        {
                            Console.WriteLine("  Release URL   : {0}", res.ReleaseUrl);
                        }
                        if (res.Updated)
                        {
                            Console.WriteLine("  {0}Status        :{1} Updated v{2} -> v{3} in {4:0.0}s",
                                cGreen, cReset, res.CurrentVersion, res.LatestVersion, res.ElapsedSeconds);
                            Console.WriteLine("  Compiler      : {0}\\bin\\arx.exe (v{1})", res.InstallDir, res.LatestVersion);
                            Console.WriteLine("  IDE extension : {0}", opts.InstallIdeExtensions ? "refreshed" : "skipped (--no-ide)");
                            if (!string.IsNullOrEmpty(res.LogPath))
                            {
                                Console.WriteLine("  Updater log   : {0}", res.LogPath);
                            }
                        }
                        else if (res.UpdateAvailable)
                        {
                            Console.WriteLine("  {0}Status        :{1} {2}", cYellow, cReset, res.Message);
                            Console.WriteLine("  Next step     : Run 'arx update' to install the latest stable release.");
                        }
                        else
                        {
                            Console.WriteLine("  {0}Status        :{1} {2}", cGreen, cReset, res.Message);
                        }

                        if (verboseUpdate && !string.IsNullOrWhiteSpace(res.ReleaseNotes))
                        {
                            Console.WriteLine();
                            Console.WriteLine("  {0}Release notes:{1}", cBold, cReset);
                            string[] lines = res.ReleaseNotes.Replace("\r\n", "\n").Split('\n');
                            int shown = 0;
                            foreach (string ln in lines)
                            {
                                string t = ln.Trim();
                                if (string.IsNullOrEmpty(t)) continue;
                                Console.WriteLine("    " + t);
                                shown++;
                                if (shown >= 6) break;
                            }
                        }
                    }
                }
                return res.Success ? 0 : 1;
            }

            if (silent)
            {
                if (!Console.IsOutputRedirected) AttachConsole(-1);
                if (uninstall)
                {
                    string target = InstallerEngine.ResolveInstalledDirFromRegistry();
                    if (string.IsNullOrEmpty(target) && !string.IsNullOrEmpty(selfExe))
                    {
                        target = Path.GetDirectoryName(selfExe);
                    }
                    string err;
                    bool ok = InstallerEngine.RunUninstall(target, delegate(int pct, string status, string logLine)
                    {
                        Console.WriteLine("[{0}%] {1}", pct, status);
                    }, out err);
                    if (!ok)
                    {
                        Console.Error.WriteLine("Uninstall error: " + err);
                        return 1;
                    }
                    InstallerEngine.ScheduleSelfDeleteIfRunningFrom(target);
                    return 0;
                }

                InstallReport rep = InstallerEngine.RunInstall(opts, delegate(int pct, string status, string logLine)
                {
                    Console.WriteLine("[{0}%] {1}", pct, status);
                });
                if (!rep.Success)
                {
                    Console.Error.WriteLine("Install error: " + rep.ErrorMessage);
                    return 1;
                }
                return 0;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new SetupForm(uninstall, opts));
            return 0;
        }
    }
}
