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
        public static void WriteUpdaterLog(string msg)
        {
            try
            {
                string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                if (string.IsNullOrEmpty(localApp)) return;
                string dir = Path.Combine(localApp, "Aerix");
                Directory.CreateDirectory(dir);
                string logPath = Path.Combine(dir, "updater.log");
                if (File.Exists(logPath) && new FileInfo(logPath).Length > 65536)
                {
                    try { File.Delete(logPath); } catch { }
                }
                string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " " + msg + Environment.NewLine;
                File.AppendAllText(logPath, line, Encoding.UTF8);
            }
            catch
            {
            }
        }

        public static void TouchUpdateCheckStamp(string latestVersion)
        {
            try
            {
                string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                if (string.IsNullOrEmpty(localApp)) return;
                string dir = Path.Combine(localApp, "Aerix");
                Directory.CreateDirectory(dir);
                string stampPath = Path.Combine(dir, "last_update_check");
                File.WriteAllText(stampPath, DateTime.UtcNow.Ticks + "|" + (latestVersion ?? "") + Environment.NewLine, Encoding.UTF8);
            }
            catch
            {
            }
        }

        public static string GetInstalledVersionFromDisk(string installDir)
        {
            try
            {
                if (!string.IsNullOrWhiteSpace(installDir))
                {
                    string arxExe = Path.Combine(TrimTrailingSlashes(installDir), "bin", "arx.exe");
                    if (File.Exists(arxExe))
                    {
                        string outTxt = RunCapture(arxExe, "version", TrimTrailingSlashes(installDir), 8000);
                        Match m = Regex.Match(outTxt ?? "", "v([0-9]+\\.[0-9]+\\.[0-9]+[^\\s]*)");
                        if (m.Success) return m.Groups[1].Value;
                    }
                }
            }
            catch
            {
            }

            try
            {
                using (RegistryKey key = Registry.CurrentUser.OpenSubKey(UninstallRegPath, false))
                {
                    if (key != null)
                    {
                        object dv = key.GetValue("DisplayVersion");
                        if (dv != null && !string.IsNullOrWhiteSpace(dv.ToString()))
                        {
                            return dv.ToString().Trim().TrimStart('v', 'V');
                        }
                    }
                }
            }
            catch
            {
            }

            return GetVersion();
        }

        private static void ParseSemVer(string raw, out int major, out int minor, out int patch, out int patchLetter, out string preTag)
        {
            major = 0; minor = 0; patch = 0; patchLetter = 0; preTag = "";
            if (string.IsNullOrWhiteSpace(raw)) return;
            string s = raw.Trim();
            if (s.StartsWith("v", StringComparison.OrdinalIgnoreCase)) s = s.Substring(1);
            int dash = s.IndexOf('-');
            string core = dash >= 0 ? s.Substring(0, dash) : s;
            preTag = dash >= 0 ? s.Substring(dash + 1).Trim().ToLowerInvariant() : "";
            string[] parts = core.Split('.');
            if (parts.Length > 0) int.TryParse(parts[0], out major);
            if (parts.Length > 1) int.TryParse(parts[1], out minor);
            if (parts.Length > 2)
            {
                Match m = Regex.Match(parts[2], @"^([0-9]+)([a-zA-Z]*)(.*)$");
                if (m.Success)
                {
                    int.TryParse(m.Groups[1].Value, out patch);
                    string letters = m.Groups[2].Value.Trim().ToLowerInvariant();
                    if (!string.IsNullOrEmpty(letters))
                    {
                        int lrank = 0;
                        foreach (char ch in letters)
                        {
                            if (ch >= 'a' && ch <= 'z')
                            {
                                lrank = lrank * 26 + (ch - 'a' + 1);
                            }
                        }
                        patchLetter = lrank;
                    }
                    string trailing = m.Groups[3].Value.Trim().ToLowerInvariant();
                    if (!string.IsNullOrEmpty(trailing) && string.IsNullOrEmpty(preTag))
                    {
                        preTag = trailing;
                    }
                }
            }
        }

        private static int TagStabilityRank(string tag)
        {
            if (string.IsNullOrEmpty(tag) || tag == "stable") return 4;
            if (tag.StartsWith("rc")) return 3;
            if (tag == "p" || tag.StartsWith("pre")) return 2;
            if (tag == "b" || tag.StartsWith("beta")) return 1;
            return 0;
        }

        public static int CompareVersions(string a, string b)
        {
            int aMaj, aMin, aPat, aLet, bMaj, bMin, bPat, bLet;
            string aTag, bTag;
            ParseSemVer(a, out aMaj, out aMin, out aPat, out aLet, out aTag);
            ParseSemVer(b, out bMaj, out bMin, out bPat, out bLet, out bTag);
            if (aMaj != bMaj) return aMaj.CompareTo(bMaj);
            if (aMin != bMin) return aMin.CompareTo(bMin);
            if (aPat != bPat) return aPat.CompareTo(bPat);
            if (aLet != bLet) return aLet.CompareTo(bLet);
            int aRank = TagStabilityRank(aTag);
            int bRank = TagStabilityRank(bTag);
            if (aRank != bRank) return aRank.CompareTo(bRank);
            return string.Compare(aTag, bTag, StringComparison.OrdinalIgnoreCase);
        }

        private static bool BoolVal(Dictionary<string, object> dict, string key)
        {
            object v;
            if (dict != null && dict.TryGetValue(key, out v) && v is bool) return (bool)v;
            return false;
        }

        private static string StrVal(Dictionary<string, object> dict, string key)
        {
            object v;
            if (dict != null && dict.TryGetValue(key, out v) && v != null) return v.ToString();
            return "";
        }

        private static string ClassifyReleaseChannel(string tag, bool isPrerelease)
        {
            string low = (tag ?? "").Trim().ToLowerInvariant();
            if (low.EndsWith("b") || low.EndsWith("-b") || low.Contains("beta")) return "beta";
            if (isPrerelease || low.EndsWith("p") || low.EndsWith("-p") || low.Contains("-pre") || low.Contains("alpha") || low.Contains("-rc"))
            {
                return "pre";
            }
            return "stable";
        }

        public static List<StableReleaseInfo> FetchReleases(bool includePreAndBeta)
        {
            var list = new List<StableReleaseInfo>();
            try
            {
                ServicePointManager.SecurityProtocol |= (SecurityProtocolType)3072 | SecurityProtocolType.Tls | SecurityProtocolType.Tls11;
                string json = "";
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(GitHubReleasesApiUrl);
                req.Method = "GET";
                req.UserAgent = "AerixSetup-Updater";
                req.Accept = "application/vnd.github+json";
                req.Timeout = 15000;
                req.ReadWriteTimeout = 15000;
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                using (Stream st = resp.GetResponseStream())
                using (StreamReader sr = new StreamReader(st, Encoding.UTF8))
                {
                    json = sr.ReadToEnd();
                }

                var ser = new JavaScriptSerializer();
                object[] releases = ser.DeserializeObject(json) as object[];
                if (releases == null) return list;

                foreach (object item in releases)
                {
                    var rel = item as Dictionary<string, object>;
                    if (rel == null) continue;
                    if (BoolVal(rel, "draft")) continue;

                    bool isPre = BoolVal(rel, "prerelease");
                    string tag = StrVal(rel, "tag_name");
                    if (string.IsNullOrWhiteSpace(tag)) continue;

                    string channel = ClassifyReleaseChannel(tag, isPre);
                    if (!includePreAndBeta && (isPre || channel != "stable"))
                    {
                        continue;
                    }

                    object assetsObj;
                    if (!rel.TryGetValue("assets", out assetsObj)) continue;
                    object[] assets = assetsObj as object[];
                    if (assets == null) continue;

                    string assetName = "";
                    string downloadUrl = "";
                    long assetSize = 0;

                    foreach (object ao in assets)
                    {
                        var asset = ao as Dictionary<string, object>;
                        if (asset == null) continue;
                        string name = StrVal(asset, "name");
                        string url = StrVal(asset, "browser_download_url");
                        if (string.IsNullOrEmpty(name) || string.IsNullOrEmpty(url)) continue;
                        if (!name.StartsWith("AerixSetup-", StringComparison.OrdinalIgnoreCase) ||
                            !name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                        {
                            continue;
                        }

                        bool isPreferred = (channel == "stable" && name.IndexOf("-stable.exe", StringComparison.OrdinalIgnoreCase) >= 0) ||
                                           (channel == "beta" && name.IndexOf("b.exe", StringComparison.OrdinalIgnoreCase) >= 0) ||
                                           (channel == "pre" && name.IndexOf("p.exe", StringComparison.OrdinalIgnoreCase) >= 0);
                        if (string.IsNullOrEmpty(downloadUrl) || isPreferred)
                        {
                            assetName = name;
                            downloadUrl = url;
                            object szObj;
                            if (asset.TryGetValue("size", out szObj) && szObj != null)
                            {
                                long.TryParse(szObj.ToString(), out assetSize);
                            }
                            if (isPreferred) break;
                        }
                    }

                    if (string.IsNullOrEmpty(downloadUrl)) continue;
                    string ver = tag.Trim().TrimStart('v', 'V');
                    list.Add(new StableReleaseInfo
                    {
                        TagName = tag,
                        Version = ver,
                        Channel = channel,
                        SetupAssetName = assetName,
                        SetupDownloadUrl = downloadUrl,
                        SetupSize = assetSize,
                        PublishedAt = StrVal(rel, "published_at"),
                        HtmlUrl = StrVal(rel, "html_url"),
                        ReleaseNotes = StrVal(rel, "body")
                    });
                }

                list.Sort(delegate(StableReleaseInfo a, StableReleaseInfo b)
                {
                    return CompareVersions(b.Version, a.Version);
                });
            }
            catch (Exception ex)
            {
                WriteUpdaterLog("FetchReleases warning: " + ex.Message);
            }
            return list;
        }

        public static StableReleaseInfo FetchLatestStableRelease()
        {
            List<StableReleaseInfo> releases = FetchReleases(false);
            return releases.Count > 0 ? releases[0] : null;
        }

        public static string FormatBytes(long bytes)
        {
            if (bytes <= 0) return "unknown size";
            if (bytes < 1024) return bytes + " B";
            if (bytes < 1024 * 1024) return string.Format("{0:0.0} KB", bytes / 1024.0);
            return string.Format("{0:0.00} MB", bytes / (1024.0 * 1024.0));
        }

        public static string ResolveUpdaterLogPath()
        {
            string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (string.IsNullOrEmpty(localApp)) return "";
            return Path.Combine(localApp, "Aerix", "updater.log");
        }

        public static string ReadLastCheckStampDisplay()
        {
            try
            {
                string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                if (string.IsNullOrEmpty(localApp)) return "never";
                string stampPath = Path.Combine(localApp, "Aerix", "last_update_check");
                if (!File.Exists(stampPath)) return "never";
                DateTime dt = File.GetLastWriteTime(stampPath);
                TimeSpan age = DateTime.Now - dt;
                if (age.TotalMinutes < 1) return dt.ToString("yyyy-MM-dd HH:mm") + " (just now)";
                if (age.TotalHours < 1) return string.Format("{0:yyyy-MM-dd HH:mm} ({1}m ago)", dt, (int)age.TotalMinutes);
                if (age.TotalDays < 1) return string.Format("{0:yyyy-MM-dd HH:mm} ({1:0.0}h ago)", dt, age.TotalHours);
                return string.Format("{0:yyyy-MM-dd HH:mm} ({1:0}d ago)", dt, age.TotalDays);
            }
            catch
            {
                return "unknown";
            }
        }

        private static void PopulateToolchainStats(string root, UpdateResult res)
        {
            try
            {
                res.HasStdlib = File.Exists(Path.Combine(root, "stdlib", "aerix_rt.h"));
                string modDir = Path.Combine(root, "modules");
                if (Directory.Exists(modDir))
                {
                    res.ModuleCount = Directory.GetFiles(modDir, "*.arx", SearchOption.AllDirectories).Length;
                }
            }
            catch
            {
            }
        }

        public sealed class CachedToolchainInfo
        {
            public string Version = "";
            public string DirectoryPath = "";
            public string InstalledAt = "";
            public long BinaryBytes;
            public bool IsActive;
        }


    }
}
