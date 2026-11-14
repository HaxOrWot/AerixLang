using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;
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

        private static bool IsAdministrator()
        {
            try
            {
                using (var id = System.Security.Principal.WindowsIdentity.GetCurrent())
                {
                    var p = new System.Security.Principal.WindowsPrincipal(id);
                    return p.IsInRole(System.Security.Principal.WindowsBuiltInRole.Administrator);
                }
            }
            catch
            {
                return false;
            }
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
            bool autoUpdateCheck = false;
            string vmAction = "";
            string vmTarget = "";
            string vmChannel = "";
            bool vmNoUse = false;
            bool vmAll = false;
            bool vmJson = false;
            var opts = new InstallOptions();

            string selfExe = Assembly.GetExecutingAssembly().Location;
            string selfName = string.IsNullOrEmpty(selfExe) ? "" : Path.GetFileName(selfExe);
            if (string.Equals(selfName, "Uninstall.exe", StringComparison.OrdinalIgnoreCase))
            {
                uninstall = true;
            }
            bool isUpdater = string.Equals(selfName, "Updater.exe", StringComparison.OrdinalIgnoreCase);

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
                    else if (low == "--auto" || low == "/auto" || low == "--bg")
                    {
                        autoUpdateCheck = true;
                        uninstall = false;
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
                    else if (low == "--vm-status")
                    {
                        vmAction = "status";
                        uninstall = false;
                    }
                    else if (low == "--vm-list")
                    {
                        vmAction = "list";
                        uninstall = false;
                    }
                    else if (low == "--vm-list-json")
                    {
                        vmAction = "list";
                        vmJson = true;
                        uninstall = false;
                    }
                    else if (low == "--vm-remote")
                    {
                        vmAction = "remote";
                        uninstall = false;
                    }
                    else if (low == "--vm-remote-json")
                    {
                        vmAction = "remote";
                        vmJson = true;
                        uninstall = false;
                    }
                    else if (low == "--vm-sync")
                    {
                        vmAction = "sync";
                        uninstall = false;
                    }
                    else if (low.StartsWith("--vm-install="))
                    {
                        vmAction = "install";
                        vmTarget = raw.Substring(13).Trim('"');
                        uninstall = false;
                    }
                    else if (low.StartsWith("--vm-use="))
                    {
                        vmAction = "use";
                        vmTarget = raw.Substring(9).Trim('"');
                        uninstall = false;
                    }
                    else if (low.StartsWith("--vm-remove="))
                    {
                        vmAction = "remove";
                        vmTarget = raw.Substring(12).Trim('"');
                        uninstall = false;
                    }
                    else if (low.StartsWith("--channel="))
                    {
                        vmChannel = raw.Substring(10).Trim('"').ToLowerInvariant();
                    }
                    else if (low == "--no-use")
                    {
                        vmNoUse = true;
                    }
                    else if (low == "--all" || low == "--allow-older")
                    {
                        vmAll = true;
                    }
                    else if (low == "--json")
                    {
                        vmJson = true;
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

            // If running the Setup Wizard interactively (first-time install) and not running as Administrator,
            // request elevation via UAC so Aerix sets up directory permissions and tools properly.
            if (!isUpdater && !uninstall && !silent && string.IsNullOrEmpty(vmAction) && !updateMode && !IsAdministrator())
            {
                try
                {
                    var psi = new ProcessStartInfo(selfExe);
                    psi.UseShellExecute = true;
                    psi.Verb = "runas";
                    if (args != null && args.Length > 0)
                    {
                        var sb = new StringBuilder();
                        foreach (string a in args)
                        {
                            if (sb.Length > 0) sb.Append(" ");
                            if (a.Contains(" ")) sb.Append("\"").Append(a).Append("\"");
                            else sb.Append(a);
                        }
                        psi.Arguments = sb.ToString();
                    }
                    Process p = Process.Start(psi);
                    if (p != null) return 0;
                }
                catch
                {
                    // User declined UAC or headless environment, continue as-is
                }
            }

            if (!string.IsNullOrEmpty(vmAction))
            {
                bool isInteractive = false;
                if (!quietUpdate) PrepareConsoleIo(out isInteractive);
                bool color = !quietUpdate && !vmJson && TryEnableAnsiColor(isInteractive);
                string cBold = color ? "\x1b[1m" : "";
                string cCyan = color ? "\x1b[1;36m" : "";
                string cGreen = color ? "\x1b[1;32m" : "";
                string cYellow = color ? "\x1b[1;33m" : "";
                string cRed = color ? "\x1b[1;31m" : "";
                string cDim = color ? "\x1b[2m" : "";
                string cReset = color ? "\x1b[0m" : "";

                string activeDir = InstallerEngine.ResolveActiveInstallDir(opts.InstallDir);
                string activeVer = InstallerEngine.GetInstalledVersionFromDisk(activeDir);
                var jsSer = new JavaScriptSerializer();

                if (vmAction == "status")
                {
                    var cached = InstallerEngine.GetCachedToolchains(activeDir, activeVer);
                    Console.WriteLine(cCyan + "Aerix Version Manager" + cReset + cDim + " (managed minimum: v" + InstallerEngine.VmMinVersion + ")" + cReset);
                    Console.WriteLine("  Active version : {0}v{1}{2}", cGreen, activeVer, cReset);
                    Console.WriteLine("  Install dir    : {0}", activeDir);
                    Console.WriteLine("  Toolchain store: {0} ({1} version(s) cached)", InstallerEngine.GetToolchainsRootDir(), cached.Count);
                    Console.WriteLine("  Updater log    : {0}", InstallerEngine.ResolveUpdaterLogPath());
                    Console.WriteLine();
                    Console.WriteLine("  Commands: arx vm list | list-remote | install <ver> | use <ver> | remove <ver> | sync");
                    return 0;
                }

                if (vmAction == "sync")
                {
                    bool ok = InstallerEngine.SnapshotToolchainVersion(activeDir, activeVer);
                    if (!quietUpdate)
                    {
                        if (ok)
                        {
                            Console.WriteLine("{0}Synced{1} active Aerix v{2} into toolchain cache ({3}).",
                                cGreen, cReset, activeVer, Path.Combine(InstallerEngine.GetToolchainsRootDir(), InstallerEngine.NormalizeVersionKey(activeVer)));
                        }
                        else
                        {
                            Console.Error.WriteLine("{0}error:{1} could not snapshot {2} (missing bin\\arx.exe).", cRed, cReset, activeDir);
                        }
                    }
                    return ok ? 0 : 1;
                }

                if (vmAction == "list")
                {
                    var cached = InstallerEngine.GetCachedToolchains(activeDir, activeVer);
                    if (vmJson)
                    {
                        var items = new List<Dictionary<string, object>>();
                        foreach (var c in cached)
                        {
                            var d = new Dictionary<string, object>();
                            d["version"] = c.Version;
                            d["active"] = c.IsActive;
                            d["installedAt"] = c.InstalledAt;
                            d["path"] = c.DirectoryPath;
                            items.Add(d);
                        }
                        var wrap = new Dictionary<string, object>();
                        wrap["activeVersion"] = activeVer;
                        wrap["installDir"] = activeDir;
                        wrap["storeDir"] = InstallerEngine.GetToolchainsRootDir();
                        wrap["toolchains"] = items;
                        Console.WriteLine(jsSer.Serialize(wrap));
                        return 0;
                    }

                    Console.WriteLine(cCyan + "Installed Aerix Toolchains" + cReset + cDim + " (" + InstallerEngine.GetToolchainsRootDir() + ")" + cReset);
                    if (cached.Count == 0)
                    {
                        Console.WriteLine("  (none installed)");
                    }
                    else
                    {
                        foreach (var c in cached)
                        {
                            string mark = c.IsActive ? (cGreen + "* " + cReset) : "  ";
                            string tag = c.IsActive ? (cGreen + " (active)" + cReset) : "";
                            Console.WriteLine("  {0}{1}v{2,-14}{3} {4}{5}  [{6}]",
                                mark, cBold, c.Version, cReset, tag,
                                cDim + (string.IsNullOrEmpty(c.InstalledAt) ? "" : " " + c.InstalledAt) + cReset,
                                c.DirectoryPath);
                        }
                    }
                    return 0;
                }

                if (vmAction == "remote")
                {
                    try
                    {
                        List<StableReleaseInfo> rels = InstallerEngine.FetchReleases(true);
                        var cachedList = InstallerEngine.GetCachedToolchains(activeDir, activeVer);
                        var cachedSet = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                        foreach (var c in cachedList) cachedSet.Add(InstallerEngine.NormalizeVersionKey(c.Version));
                        string normActive = InstallerEngine.NormalizeVersionKey(activeVer);

                        var filtered = new List<StableReleaseInfo>();
                        foreach (var r in rels)
                        {
                            if (!vmAll && InstallerEngine.CompareVersions(r.Version, InstallerEngine.VmMinVersion) < 0) continue;
                            if (!string.IsNullOrEmpty(vmChannel) && !string.Equals(r.Channel, vmChannel, StringComparison.OrdinalIgnoreCase)) continue;
                            filtered.Add(r);
                        }

                        if (vmJson)
                        {
                            var jlist = new List<Dictionary<string, object>>();
                            foreach (var r in filtered)
                            {
                                string rk = InstallerEngine.NormalizeVersionKey(r.Version);
                                var d = new Dictionary<string, object>();
                                d["version"] = r.Version;
                                d["tag"] = r.TagName;
                                d["channel"] = r.Channel;
                                d["publishedAt"] = FormatPublishedDate(r.PublishedAt);
                                d["assetName"] = r.SetupAssetName;
                                d["size"] = r.SetupSize;
                                d["cached"] = cachedSet.Contains(rk);
                                d["active"] = string.Equals(rk, normActive, StringComparison.OrdinalIgnoreCase);
                                jlist.Add(d);
                            }
                            Console.WriteLine(jsSer.Serialize(jlist));
                            return 0;
                        }

                        Console.WriteLine(cCyan + "Available Aerix Releases on GitHub" + cReset +
                            cDim + (vmAll ? " (all versions)" : " (starting from v" + InstallerEngine.VmMinVersion + "; pass --all for legacy)") + cReset);
                        if (filtered.Count == 0)
                        {
                            Console.WriteLine("  (no releases found matching criteria on GitHub yet; active/cached v{0} can still be managed offline via 'arx vm list')", activeVer);
                        }
                        else
                        {
                            foreach (var r in filtered)
                            {
                                string rk = InstallerEngine.NormalizeVersionKey(r.Version);
                                bool isAct = string.Equals(rk, normActive, StringComparison.OrdinalIgnoreCase);
                                bool isCac = cachedSet.Contains(rk);
                                string chColor = r.Channel == "stable" ? cGreen : (r.Channel == "beta" ? cCyan : cYellow);
                                string state = isAct ? (cGreen + " [active]" + cReset) : (isCac ? (cDim + " [installed]" + cReset) : "");
                                Console.WriteLine("  {0}v{1,-14}{2} {3}[{4,-6}]{5}  {6}  ({7}){8}",
                                    cBold, r.Version, cReset, chColor, r.Channel, cReset,
                                    FormatPublishedDate(r.PublishedAt), InstallerEngine.FormatBytes(r.SetupSize), state);
                            }
                        }
                        return 0;
                    }
                    catch (Exception ex)
                    {
                        if (!quietUpdate) Console.Error.WriteLine("{0}error:{1} {2}", cRed, cReset, ex.Message);
                        return 1;
                    }
                }

                if (vmAction == "remove")
                {
                    string rmMsg;
                    bool ok = InstallerEngine.RunVmRemove(vmTarget, forceUpdate, opts.InstallDir, out rmMsg);
                    if (!quietUpdate)
                    {
                        if (ok) Console.WriteLine("{0}Removed:{1} {2}", cGreen, cReset, rmMsg);
                        else Console.Error.WriteLine("{0}error:{1} {2}", cRed, cReset, rmMsg);
                    }
                    return ok ? 0 : 1;
                }

                if (vmAction == "install" || vmAction == "use")
                {
                    if (!quietUpdate)
                    {
                        Console.WriteLine(cCyan + "Aerix Version Manager" + cReset +
                            cDim + (vmAction == "use" ? " (switch)" : " (install)") + cReset);
                        Console.WriteLine("  Target version : {0}{1}{2}", cBold, vmTarget, cReset);
                        Console.WriteLine("  Install dir    : {0}", activeDir);
                        Console.WriteLine();
                    }

                    bool inlineBar = false;
                    UpdateResult vmRes = InstallerEngine.RunVmInstallOrUse(
                        vmTarget,
                        vmAction == "use",
                        !vmNoUse,
                        forceUpdate,
                        vmAll,
                        !opts.InstallIdeExtensions,
                        opts.InstallDir,
                        delegate(int pct, string status, string logLine)
                        {
                            if (quietUpdate) return;
                            if (pct < 100)
                            {
                                if (isInteractive && logLine == "progress")
                                {
                                    string line = string.Format("  {0}{1}{2} {3,3}% {4}", cCyan, RenderProgressBar(pct, 22), cReset, pct, status);
                                    Console.Write("\r" + line.PadRight(78));
                                    inlineBar = true;
                                }
                                else
                                {
                                    if (inlineBar) { Console.WriteLine(); inlineBar = false; }
                                    Console.WriteLine("  {0}[{1,3}%]{2} {3}", cDim, pct, cReset, status);
                                }
                            }
                        });
                    if (inlineBar) Console.WriteLine();

                    if (!quietUpdate)
                    {
                        Console.WriteLine();
                        if (!vmRes.Success)
                        {
                            Console.Error.WriteLine("{0}error:{1} {2}", cRed, cReset, vmRes.Message);
                        }
                        else
                        {
                            Console.WriteLine("  {0}Status:{1} {2} ({3:0.0}s)", cGreen, cReset, vmRes.Message, vmRes.ElapsedSeconds);
                            if (!string.IsNullOrEmpty(vmRes.LatestVersion))
                            {
                                Console.WriteLine("  Active: {0}\\bin\\arx.exe (v{1})", vmRes.InstallDir, vmRes.LatestVersion);
                            }
                        }
                        try { Console.Out.Flush(); Console.Error.Flush(); } catch { }
                    }
                    return vmRes.Success ? 0 : 1;
                }
            }

            if (autoUpdateCheck || (isUpdater && !updateMode && string.IsNullOrEmpty(vmAction) && !uninstall))
            {
                string activeDir = InstallerEngine.ResolveActiveInstallDir(opts.InstallDir);
                string currentVer = InstallerEngine.GetInstalledVersionFromDisk(activeDir);

                StableReleaseInfo latest = null;
                string checkErr = null;
                try
                {
                    latest = InstallerEngine.FetchLatestStableRelease();
                }
                catch (Exception ex)
                {
                    checkErr = ex.Message;
                }

                if (latest == null)
                {
                    if (!autoUpdateCheck && !quietUpdate && !silent)
                    {
                        Application.EnableVisualStyles();
                        Application.SetCompatibleTextRenderingDefault(false);
                        MessageBox.Show(
                            "Could not check for Aerix updates:\n\n" + (checkErr ?? "No stable release found on GitHub."),
                            "Aerix Updater",
                            MessageBoxButtons.OK,
                            MessageBoxIcon.Warning);
                    }
                    return autoUpdateCheck ? 0 : 1;
                }

                InstallerEngine.TouchUpdateCheckStamp(latest.Version);
                int cmp = InstallerEngine.CompareVersions(latest.Version, currentVer);

                if (cmp <= 0 && !forceUpdate)
                {
                    if (!autoUpdateCheck && !quietUpdate && !silent)
                    {
                        Application.EnableVisualStyles();
                        Application.SetCompatibleTextRenderingDefault(false);
                        MessageBox.Show(
                            string.Format("Aerix is up to date.\n\n" +
                                          "  Installed version:  v{0}\n" +
                                          "  Latest stable:      v{1}\n" +
                                          "  Release channel:    stable\n\n" +
                                          "Your installation is running the latest stable release.",
                                          currentVer, latest.Version),
                            "Aerix Updater",
                            MessageBoxButtons.OK,
                            MessageBoxIcon.Information);
                    }
                    return 0;
                }

                Application.EnableVisualStyles();
                Application.SetCompatibleTextRenderingDefault(false);

                string promptMsg = string.Format(
                    "A new stable update for Aerix is available!\n\n" +
                    "  Current version:  v{0}\n" +
                    "  Latest version:   v{1}\n" +
                    "  Published:        {2}\n" +
                    "  Package size:     {3}\n\n" +
                    "Do you want to install this update now?",
                    currentVer,
                    latest.Version,
                    FormatPublishedDate(latest.PublishedAt),
                    InstallerEngine.FormatBytes(latest.SetupSize));

                DialogResult dr = MessageBox.Show(
                    promptMsg,
                    "Aerix Update Available",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question);

                if (dr != DialogResult.Yes)
                {
                    return 0;
                }

                using (var prog = new UpdateProgressForm(latest, activeDir, !opts.InstallIdeExtensions))
                {
                    Application.Run(prog);
                    return prog.Success ? 0 : 1;
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
