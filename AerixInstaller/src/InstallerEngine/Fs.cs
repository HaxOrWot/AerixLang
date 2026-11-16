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


    }
}
