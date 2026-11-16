using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace AerixSetup
{
    internal static partial class Program
    {
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


            int? cliResult = RunCli(vmAction, vmTarget, vmChannel, vmNoUse, vmAll, vmJson, updateMode, autoUpdateCheck, checkUpdateOnly, forceUpdate, quietUpdate, verboseUpdate, opts, isUpdater, uninstall, silent);
            if (cliResult.HasValue)
            {
                return cliResult.Value;
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
    

