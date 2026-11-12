using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
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
        private static extern uint GetFileType(IntPtr hFile);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetConsoleMode(IntPtr hConsoleHandle, out uint lpMode);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool SetConsoleMode(IntPtr hConsoleHandle, uint dwMode);

        private const uint FILE_TYPE_DISK = 1;
        private const uint FILE_TYPE_CHAR = 2;
        private const uint FILE_TYPE_PIPE = 3;

        private static bool PrepareConsoleIo(out bool isInteractiveConsole)
        {
            isInteractiveConsole = false;
            IntPtr hOut = GetStdHandle(-11);
            uint ftype = (hOut == IntPtr.Zero || hOut == new IntPtr(-1)) ? 0u : GetFileType(hOut);

            // If stdout is not redirected to a pipe or disk file, attach parent console
            // BEFORE calling any System.Console members (Console.IsOutputRedirected would
            // cache a broken Stream.Null handle on /target:winexe processes).
            if (ftype != FILE_TYPE_PIPE && ftype != FILE_TYPE_DISK)
            {
                bool attached = AttachConsole(-1);
                if (attached)
                {
                    try
                    {
                        Encoding enc = Console.OutputEncoding;
                        Console.SetOut(new StreamWriter(Console.OpenStandardOutput(), enc) { AutoFlush = true });
                        Console.SetError(new StreamWriter(Console.OpenStandardError(), enc) { AutoFlush = true });
                    }
                    catch
                    {
                    }
                    hOut = GetStdHandle(-11);
                    ftype = (hOut == IntPtr.Zero || hOut == new IntPtr(-1)) ? 0u : GetFileType(hOut);
                }
            }

            isInteractiveConsole = (ftype == FILE_TYPE_CHAR);
            return isInteractiveConsole || ftype == FILE_TYPE_PIPE || ftype == FILE_TYPE_DISK;
        }

        private static bool TryEnableAnsiColor(bool isInteractive)
        {
            if (!isInteractive) return false;
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

        private static string RenderProgressBar(int pct, int width)
        {
            if (pct < 0) pct = 0;
            if (pct > 100) pct = 100;
            int filled = (pct * width) / 100;
            return "[" + new string('#', filled) + new string('-', width - filled) + "]";
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
                bool isInteractive = false;
                if (!quietUpdate) PrepareConsoleIo(out isInteractive);
                bool color = !quietUpdate && TryEnableAnsiColor(isInteractive);
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
                bool inlineBarActive = false;
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
                            Console.WriteLine("  Installed    : {0}v{1}{2}", cBold, (hp.Length > 1 ? hp[1] : "").TrimStart('v', 'V'), cReset);
                            Console.WriteLine("  Last checked : {0}", InstallerEngine.ReadLastCheckStampDisplay());
                            Console.WriteLine("  Repository   : https://github.com/HaxOrWot/AerixLang/releases");
                            Console.WriteLine();
                        }
                        if (pct < 100)
                        {
                            if (isInteractive && logLine == "progress")
                            {
                                string line = string.Format("  {0}{1}{2} {3,3}% {4}", cCyan, RenderProgressBar(pct, 22), cReset, pct, status);
                                Console.Write("\r" + line.PadRight(78));
                                inlineBarActive = true;
                            }
                            else
                            {
                                if (inlineBarActive)
                                {
                                    Console.WriteLine();
                                    inlineBarActive = false;
                                }
                                Console.WriteLine("  {0}[{1,3}%]{2} {3}", cDim, pct, cReset, status);
                            }
                        }
                    });

                if (inlineBarActive)
                {
                    Console.WriteLine();
                }

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
                            Console.WriteLine("  Compiler      : {0}\\bin\\arx.exe (v{1}, PE32+ native)", res.InstallDir, res.LatestVersion);
                            Console.WriteLine("  Runtime/Mods  : {0}, {1} stdlib module(s)",
                                res.HasStdlib ? "stdlib/aerix_rt.h ready" : "stdlib missing", res.ModuleCount);
                            Console.WriteLine("  IDE extension : {0}", opts.InstallIdeExtensions ? "refreshed" : "skipped (--no-ide)");
                        }
                        else if (res.UpdateAvailable)
                        {
                            Console.WriteLine("  {0}Status        :{1} {2}", cYellow, cReset, res.Message);
                            Console.WriteLine("  Next step     : Run 'arx update' to install the latest stable release.");
                        }
                        else
                        {
                            Console.WriteLine("  {0}Status        :{1} {2}", cGreen, cReset, res.Message);
                            Console.WriteLine("  Runtime/Mods  : {0}, {1} stdlib module(s)",
                                res.HasStdlib ? "stdlib/aerix_rt.h ready" : "stdlib missing", res.ModuleCount);
                        }
                        if (!string.IsNullOrEmpty(res.LogPath))
                        {
                            Console.WriteLine("  Updater log   : {0}", res.LogPath);
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
                                if (shown >= 14) break;
                            }
                        }
                    }
                    try { Console.Out.Flush(); Console.Error.Flush(); } catch { }
                }
                return res.Success ? 0 : 1;
            }

            if (silent)
            {
                bool unusedInteractive;
                PrepareConsoleIo(out unusedInteractive);
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
