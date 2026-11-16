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
    public sealed class InstallOptions
    {
        public string InstallDir = InstallerEngine.GetDefaultInstallDir();
        public bool ConfigureEnv = true;
        public bool FileAssociations = true;
        public bool InstallIdeExtensions = true;
        public bool RunSmokeTest = true;
    }

    public sealed class EditorInfo
    {
        public string Name;
        public string CliPath;
        public string ExtensionDir;
        public bool IsDetected;

        public EditorInfo(string name, string cliPath, string extDir, bool detected)
        {
            Name = name;
            CliPath = cliPath;
            ExtensionDir = extDir;
            IsDetected = detected;
        }
    }

    public sealed class InstallReport
    {
        public bool Success;
        public string ErrorMessage = "";
        public string InstalledVersion = "";
        public string SmokeTestSummary = "";
        public int ExtractedFiles;
        public readonly List<string> InstalledEditors = new List<string>();
    }

    public sealed class StableReleaseInfo
    {
        public string TagName = "";
        public string Version = "";
        public string Channel = "stable";
        public string SetupAssetName = "";
        public string SetupDownloadUrl = "";
        public long SetupSize;
        public string PublishedAt = "";
        public string HtmlUrl = "";
        public string ReleaseNotes = "";
    }

    public sealed class UpdateResult
    {
        public bool Success;
        public bool Updated;
        public bool UpdateAvailable;
        public string CurrentVersion = "";
        public string LatestVersion = "";
        public string InstallDir = "";
        public string PublishedAt = "";
        public string AssetName = "";
        public long AssetSize;
        public string ReleaseUrl = "";
        public string ReleaseNotes = "";
        public string LastCheckedAt = "";
        public string LogPath = "";
        public int ModuleCount;
        public bool HasStdlib;
        public double ElapsedSeconds;
        public string Message = "";
    }

    public delegate void ProgressHandler(int percent, string status, string logLine);

}
