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
        public static UpdateResult RunVmInstallOrUse(
            string spec,
            bool useMode,
            bool activateAfter,
            bool force,
            bool allowOlder,
            bool skipIde,
            string installDirOverride,
            ProgressHandler progress)
        {
            var res = new UpdateResult();
            res.LogPath = ResolveUpdaterLogPath();
            res.LastCheckedAt = ReadLastCheckStampDisplay();
            var sw = Stopwatch.StartNew();
            Mutex mtx = null;
            bool acquired = false;
            try
            {
                try
                {
                    mtx = new Mutex(false, @"Local\AerixLangAutoUpdater");
                    acquired = mtx.WaitOne(3000);
                }
                catch (AbandonedMutexException) { acquired = true; }
                catch { acquired = true; }

                if (!acquired)
                {
                    res.Success = false;
                    res.Message = "Another Aerix version operation is already in progress.";
                    return res;
                }

                string targetDir = ResolveActiveInstallDir(installDirOverride);
                res.InstallDir = targetDir;
                res.CurrentVersion = GetInstalledVersionFromDisk(targetDir);
                PopulateToolchainStats(targetDir, res);

                string req = (spec ?? "").Trim();
                if (string.IsNullOrEmpty(req))
                {
                    res.Success = false;
                    res.Message = "No version specified. Run 'arx vm list-remote' to see available versions (from " + VmMinVersion + ").";
                    return res;
                }

                string cleanKey = NormalizeVersionKey(req);
                string lowReq = cleanKey.ToLowerInvariant();
                bool isChannelAlias = (lowReq == "latest" || lowReq == "stable" || lowReq == "beta" || lowReq == "pre");

                if (!isChannelAlias && !allowOlder && CompareVersions(cleanKey, VmMinVersion) < 0)
                {
                    res.Success = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format("Version 'v{0}' is older than minimum managed version 'v{1}'. Pass --all to override.", cleanKey, VmMinVersion);
                    return res;
                }

                // Snapshot current active installation before any switch
                if (!string.IsNullOrEmpty(res.CurrentVersion))
                {
                    SnapshotToolchainVersion(targetDir, res.CurrentVersion);
                }

                // 1. Check local cache first (for exact versions, or channel aliases if not forced)
                if (!force)
                {
                    string targetCachedKey = null;
                    if (!isChannelAlias)
                    {
                        if (string.Equals(NormalizeVersionKey(res.CurrentVersion), cleanKey, StringComparison.OrdinalIgnoreCase))
                        {
                            res.Success = true;
                            res.LatestVersion = res.CurrentVersion;
                            res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                            res.Message = string.Format("Aerix v{0} is already the active toolchain.", res.CurrentVersion);
                            Report(progress, 100, res.Message, res.Message);
                            return res;
                        }

                        string cachedDir = Path.Combine(GetToolchainsRootDir(), cleanKey);
                        if (File.Exists(Path.Combine(cachedDir, "bin", "arx.exe")))
                        {
                            targetCachedKey = cleanKey;
                        }
                    }
                    else
                    {
                        List<CachedToolchainInfo> cached = GetCachedToolchains(targetDir, res.CurrentVersion);
                        foreach (var c in cached)
                        {
                            string cChan = ClassifyReleaseChannel(c.Version, false);
                            if (lowReq == "latest" || cChan == lowReq)
                            {
                                if (c.IsActive)
                                {
                                    res.Success = true;
                                    res.LatestVersion = c.Version;
                                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                                    res.Message = string.Format("Aerix v{0} is already the active toolchain ({1} channel).", c.Version, lowReq);
                                    Report(progress, 100, res.Message, res.Message);
                                    return res;
                                }
                                targetCachedKey = c.Version;
                                break;
                            }
                        }
                    }

                    if (!string.IsNullOrEmpty(targetCachedKey))
                    {
                        string cachedDir = Path.Combine(GetToolchainsRootDir(), targetCachedKey);
                        Report(progress, 35, "Found cached toolchain v" + targetCachedKey + " in local store...", cachedDir);
                        if (!activateAfter)
                        {
                            res.Success = true;
                            res.LatestVersion = targetCachedKey;
                            res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                            res.Message = string.Format("Toolchain v{0} is already installed locally (cached at {1}).", targetCachedKey, cachedDir);
                            Report(progress, 100, res.Message, res.Message);
                            return res;
                        }

                        Report(progress, 70, "Switching active toolchain to cached v" + targetCachedKey + "...", targetDir);
                        string actErr;
                        if (!ActivateCachedToolchain(targetDir, targetCachedKey, out actErr))
                        {
                            res.Success = false;
                            res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                            res.Message = actErr;
                            return res;
                        }

                        CleanupStaleBackups(targetDir);
                        CleanupStaleBackups(Path.Combine(targetDir, "bin"));
                        PopulateToolchainStats(targetDir, res);
                        res.Success = true;
                        res.Updated = true;
                        res.LatestVersion = GetInstalledVersionFromDisk(targetDir);
                        if (string.IsNullOrEmpty(res.LatestVersion)) res.LatestVersion = targetCachedKey;
                        res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                        res.Message = string.Format("Switched Aerix v{0} -> v{1} (from local cache).", res.CurrentVersion, res.LatestVersion);
                        WriteUpdaterLog(res.Message);
                        Report(progress, 100, res.Message, res.Message);
                        return res;
                    }
                }

                // 2. Fetch releases from GitHub
                Report(progress, 10, "Querying GitHub releases for 'v" + cleanKey + "'...", targetDir + "|v" + res.CurrentVersion);
                List<StableReleaseInfo> allRels = FetchReleases(true);
                StableReleaseInfo chosen = null;

                foreach (var r in allRels)
                {
                    if (!allowOlder && CompareVersions(r.Version, VmMinVersion) < 0) continue;
                    if (isChannelAlias)
                    {
                        if (lowReq == "latest" || r.Channel == lowReq)
                        {
                            chosen = r;
                            break;
                        }
                    }
                    else
                    {
                        string rk = NormalizeVersionKey(r.Version).ToLowerInvariant();
                        string reqNoDash = lowReq.Replace("-", "");
                        string rkNoDash = rk.Replace("-", "");
                        if (rk == lowReq || rkNoDash == reqNoDash)
                        {
                            chosen = r;
                            break;
                        }
                    }
                }

                if (chosen == null)
                {
                    // Fallback to local cache if network unreachable or release query returned nothing
                    List<CachedToolchainInfo> cached = GetCachedToolchains(targetDir, res.CurrentVersion);
                    string fallbackKey = null;
                    if (isChannelAlias)
                    {
                        foreach (var c in cached)
                        {
                            string cChan = ClassifyReleaseChannel(c.Version, false);
                            if (lowReq == "latest" || cChan == lowReq)
                            {
                                fallbackKey = c.Version;
                                break;
                            }
                        }
                    }
                    else
                    {
                        foreach (var c in cached)
                        {
                            if (string.Equals(NormalizeVersionKey(c.Version), cleanKey, StringComparison.OrdinalIgnoreCase))
                            {
                                fallbackKey = c.Version;
                                break;
                            }
                        }
                    }

                    if (!string.IsNullOrEmpty(fallbackKey))
                    {
                        Report(progress, 70, "Remote release query unavailable; switching to cached v" + fallbackKey + "...", targetDir);
                        string actErr;
                        if (ActivateCachedToolchain(targetDir, fallbackKey, out actErr))
                        {
                            CleanupStaleBackups(targetDir);
                            CleanupStaleBackups(Path.Combine(targetDir, "bin"));
                            PopulateToolchainStats(targetDir, res);
                            res.Success = true;
                            res.Updated = true;
                            res.LatestVersion = fallbackKey;
                            res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                            res.Message = string.Format("Switched Aerix v{0} -> v{1} (from local cache; remote offline/unreachable).", res.CurrentVersion, res.LatestVersion);
                            WriteUpdaterLog(res.Message);
                            Report(progress, 100, res.Message, res.Message);
                            return res;
                        }
                    }

                    res.Success = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format(
                        "Release 'v{0}' with a prebuilt Windows installer was not found on GitHub (minimum managed: v{1}). Run 'arx vm list-remote{2}' to see available releases.",
                        cleanKey, VmMinVersion, allowOlder ? " --all" : "");
                    return res;
                }

                res.LatestVersion = chosen.Version;
                res.PublishedAt = chosen.PublishedAt;
                res.AssetName = chosen.SetupAssetName;
                res.AssetSize = chosen.SetupSize;
                res.ReleaseUrl = string.IsNullOrEmpty(chosen.HtmlUrl)
                    ? ("https://github.com/HaxOrWot/AerixLang/releases/tag/" + chosen.TagName)
                    : chosen.HtmlUrl;
                res.ReleaseNotes = chosen.ReleaseNotes;

                string dlErr;
                long dlSize;
                if (activateAfter || useMode)
                {
                    if (!DownloadVerifyAndApplyRelease(chosen, targetDir, skipIde, res.CurrentVersion, progress, out dlErr, out dlSize))
                    {
                        res.Success = false;
                        res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                        res.Message = dlErr;
                        WriteUpdaterLog("VM install failed: " + dlErr);
                        return res;
                    }
                    res.AssetSize = dlSize;
                    CleanupStaleBackups(targetDir);
                    CleanupStaleBackups(Path.Combine(targetDir, "bin"));
                    PopulateToolchainStats(targetDir, res);
                    string postVer = GetInstalledVersionFromDisk(targetDir);
                    if (!string.IsNullOrEmpty(postVer)) res.LatestVersion = postVer;
                    res.Success = true;
                    res.Updated = true;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format("Installed & activated Aerix v{0} (was v{1}).", res.LatestVersion, res.CurrentVersion);
                    WriteUpdaterLog(res.Message);
                    Report(progress, 100, res.Message, res.Message);
                    return res;
                }
                else
                {
                    // --no-use: download + apply cleanly into isolated cache folder while keeping active install untouched
                    string origDir = targetDir;
                    string cacheTarget = Path.Combine(GetToolchainsRootDir(), NormalizeVersionKey(chosen.Version));
                    if (!DownloadVerifyAndApplyRelease(chosen, cacheTarget, true, "", progress, out dlErr, out dlSize))
                    {
                        res.Success = false;
                        res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                        res.Message = dlErr;
                        return res;
                    }
                    // Restore registry InstallLocation/DisplayVersion to active dir
                    try
                    {
                        using (RegistryKey rk = Registry.CurrentUser.CreateSubKey(UninstallRegPath))
                        {
                            if (rk != null)
                            {
                                rk.SetValue("InstallLocation", origDir, RegistryValueKind.String);
                                rk.SetValue("DisplayVersion", res.CurrentVersion, RegistryValueKind.String);
                            }
                        }
                    }
                    catch { }
                    res.AssetSize = dlSize;
                    res.Success = true;
                    res.Updated = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format("Installed Aerix v{0} into cache (active remains v{1}). Switch anytime with 'arx vm use {0}'.", chosen.Version, res.CurrentVersion);
                    WriteUpdaterLog(res.Message);
                    Report(progress, 100, res.Message, res.Message);
                    return res;
                }
            }
            catch (Exception ex)
            {
                res.Success = false;
                res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                res.Message = ex.Message;
                WriteUpdaterLog("VM error: " + ex.Message);
                return res;
            }
            finally
            {
                if (mtx != null)
                {
                    if (acquired) { try { mtx.ReleaseMutex(); } catch { } }
                    mtx.Dispose();
                }
            }
        }

        public static bool RunVmRemove(string version, bool force, string installDirOverride, out string msg)
        {
            msg = "";
            string key = NormalizeVersionKey(version);
            if (string.IsNullOrEmpty(key))
            {
                msg = "No version specified.";
                return false;
            }
            string activeDir = ResolveActiveInstallDir(installDirOverride);
            string activeVer = NormalizeVersionKey(GetInstalledVersionFromDisk(activeDir));
            if (string.Equals(key, activeVer, StringComparison.OrdinalIgnoreCase) && !force)
            {
                msg = string.Format("Cannot remove active toolchain 'v{0}'. Switch to another version first or pass --force.", key);
                return false;
            }
            string tcDir = Path.Combine(GetToolchainsRootDir(), key);
            if (!Directory.Exists(tcDir))
            {
                msg = string.Format("Cached toolchain 'v{0}' was not found in {1}.", key, GetToolchainsRootDir());
                return false;
            }
            Directory.Delete(tcDir, true);
            msg = string.Format("Removed cached toolchain v{0} from {1}.", key, tcDir);
            WriteUpdaterLog(msg);
            return true;
        }

        public static UpdateResult RunAutoUpdate(bool checkOnly, bool force, bool skipIde, string installDirOverride, ProgressHandler progress)
        {
            var res = new UpdateResult();
            res.LogPath = ResolveUpdaterLogPath();
            res.LastCheckedAt = ReadLastCheckStampDisplay();
            var sw = Stopwatch.StartNew();
            Mutex mtx = null;
            bool acquired = false;
            try
            {
                try
                {
                    mtx = new Mutex(false, @"Local\AerixLangAutoUpdater");
                    acquired = mtx.WaitOne(checkOnly ? 1000 : 3000);
                }
                catch (AbandonedMutexException) { acquired = true; }
                catch { acquired = true; }

                if (!acquired)
                {
                    res.Success = true;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = "Another Aerix update is already running.";
                    return res;
                }

                string targetDir = ResolveActiveInstallDir(installDirOverride);
                res.InstallDir = targetDir;
                PopulateToolchainStats(targetDir, res);

                res.CurrentVersion = GetInstalledVersionFromDisk(targetDir);
                Report(progress, 10, "Checking GitHub for latest stable release...", targetDir + "|v" + res.CurrentVersion);

                StableReleaseInfo latest = FetchLatestStableRelease();
                if (latest == null)
                {
                    res.Success = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = "No stable Aerix release with a Windows installer was found on GitHub.";
                    WriteUpdaterLog("Check failed: " + res.Message);
                    return res;
                }

                res.LatestVersion = latest.Version;
                res.PublishedAt = latest.PublishedAt;
                res.AssetName = latest.SetupAssetName;
                res.AssetSize = latest.SetupSize;
                res.ReleaseUrl = string.IsNullOrEmpty(latest.HtmlUrl)
                    ? ("https://github.com/HaxOrWot/AerixLang/releases/tag/" + latest.TagName)
                    : latest.HtmlUrl;
                res.ReleaseNotes = latest.ReleaseNotes;
                TouchUpdateCheckStamp(latest.Version);

                int cmp = CompareVersions(latest.Version, res.CurrentVersion);
                res.UpdateAvailable = cmp > 0;
                if (cmp <= 0 && !force)
                {
                    res.Success = true;
                    res.Updated = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format("Already running the latest stable release (v{0}).", res.CurrentVersion);
                    Report(progress, 100, res.Message, res.Message);
                    return res;
                }

                if (checkOnly)
                {
                    res.Success = true;
                    res.Updated = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = string.Format("Update available: v{0} -> v{1} ({2}, {3})",
                        res.CurrentVersion, res.LatestVersion, latest.SetupAssetName, FormatBytes(latest.SetupSize));
                    Report(progress, 100, res.Message, res.Message);
                    return res;
                }

                string applyErr;
                long actualSize;
                if (!DownloadVerifyAndApplyRelease(latest, targetDir, skipIde, res.CurrentVersion, progress, out applyErr, out actualSize))
                {
                    res.Success = false;
                    res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                    res.Message = applyErr;
                    WriteUpdaterLog("Update failed: " + applyErr);
                    return res;
                }
                res.AssetSize = actualSize;

                Report(progress, 92, "Verifying updated compiler binary...", targetDir);
                CleanupStaleBackups(targetDir);
                CleanupStaleBackups(Path.Combine(targetDir, "bin"));
                PopulateToolchainStats(targetDir, res);
                string postVer = GetInstalledVersionFromDisk(targetDir);
                res.Success = true;
                res.Updated = true;
                res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                if (!string.IsNullOrEmpty(postVer)) res.LatestVersion = postVer;
                res.Message = string.Format("Updated Aerix from v{0} to v{1}.", res.CurrentVersion, res.LatestVersion);
                WriteUpdaterLog(res.Message);
                Report(progress, 100, res.Message, res.Message);
                return res;
            }
            catch (Exception ex)
            {
                res.Success = false;
                res.ElapsedSeconds = sw.Elapsed.TotalSeconds;
                res.Message = ex.Message;
                WriteUpdaterLog("Update exception: " + ex.Message);
                return res;
            }
            finally
            {
                if (mtx != null)
                {
                    if (acquired)
                    {
                        try { mtx.ReleaseMutex(); } catch { }
                    }
                    mtx.Dispose();
                }
            }
        }
    }


    }

