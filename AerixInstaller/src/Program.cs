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

        [STAThread]
        private static int Main(string[] args)
        {
            bool silent = false;
            bool uninstall = false;
            bool updateMode = false;
            bool checkUpdateOnly = false;
            bool forceUpdate = false;
            bool quietUpdate = false;
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
                UpdateResult res = InstallerEngine.RunAutoUpdate(
                    checkUpdateOnly,
                    forceUpdate,
                    opts.InstallDir,
                    delegate(int pct, string status, string logLine)
                    {
                        if (!quietUpdate) Console.WriteLine("[{0}%] {1}", pct, status);
                    });
                if (!quietUpdate)
                {
                    if (!res.Success)
                    {
                        Console.Error.WriteLine("Update error: " + res.Message);
                    }
                    else
                    {
                        Console.WriteLine(res.Message);
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
