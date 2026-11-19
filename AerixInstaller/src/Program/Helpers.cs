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


    }
}
