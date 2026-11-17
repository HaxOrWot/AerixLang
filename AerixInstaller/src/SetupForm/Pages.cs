using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;

namespace AerixSetup
{
    public sealed partial class SetupForm : Form
    {
        private void BuildWizardPages()
        {
            _pages = new Panel[4];
            _pages[0] = BuildWelcomePage();
            _pages[1] = BuildOptionsPage();
            _pages[2] = BuildProgressPage();
            _pages[3] = BuildFinishPage();

            foreach (Panel p in _pages)
            {
                p.Dock = DockStyle.Fill;
                p.Visible = false;
                p.BackColor = BgWindow;
                _contentHost.Controls.Add(p);
            }

            // Footer navigation buttons
            _btnBack = MakeButton("< Back", false);
            _btnBack.Location = new Point(_footer.Width - 324, 12);
            _btnBack.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _btnBack.Click += delegate { if (_pageIndex == 1) ShowPage(0); };

            _btnNext = MakeButton("Next >", true);
            _btnNext.Location = new Point(_footer.Width - 216, 12);
            _btnNext.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _btnNext.Click += OnNextClicked;

            _btnCancel = MakeButton("Cancel", false);
            _btnCancel.Location = new Point(_footer.Width - 110, 12);
            _btnCancel.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _btnCancel.Click += delegate { if (!_isBusy) Close(); };

            _footer.Controls.Add(_btnBack);
            _footer.Controls.Add(_btnNext);
            _footer.Controls.Add(_btnCancel);
        }

        private Panel BuildWelcomePage()
        {
            var p = new Panel();

            var title = MakeHeaderLabel("Install Aerix " + _version, 0, 0);
            var sub = MakeSubLabel(
                "Modern, high-performance systems programming language with autonomous self-hosting native PE32+ code generation.",
                0, 32, 528, 24);

            // Feature Highlights Hero Card
            var card = MakeCard(0, 62, 528, 102);

            var row1 = MakeFeatureRow("⚡", "Zero-Dependency Native Backend", "Emits direct Win64 PE32+ executables without GCC, Clang, or external linkers.", 14, 10);
            var row2 = MakeFeatureRow("📦", "Rich Standard Library & Modules", "Includes native Sockets, Math, Window/Canvas GUI, Exception handling & generics.", 14, 38);
            var row3 = MakeFeatureRow("🧩", "Automated IDE Language Server", "Full syntax highlighting, hover documentation, typecheck, and F12 navigation.", 14, 66);

            card.Controls.Add(row1);
            card.Controls.Add(row2);
            card.Controls.Add(row3);

            var lblLic = new Label();
            lblLic.UseMnemonic = false;
            lblLic.Text = "License Agreement (MIT)";
            lblLic.ForeColor = TextMuted;
            lblLic.Font = new Font("Segoe UI Semibold", 8.8F);
            lblLic.Location = new Point(0, 172);
            lblLic.AutoSize = true;

            var txtLic = new TextBox();
            txtLic.Multiline = true;
            txtLic.ReadOnly = true;
            txtLic.TabStop = false;
            txtLic.ScrollBars = ScrollBars.Vertical;
            txtLic.BackColor = BgInput;
            txtLic.ForeColor = Color.FromArgb(178, 196, 222);
            txtLic.BorderStyle = BorderStyle.FixedSingle;
            txtLic.Font = new Font("Consolas", 8.3F);
            txtLic.Location = new Point(0, 194);
            txtLic.Size = new Size(528, 132);
            txtLic.Text = InstallerEngine.GetLicenseText();
            txtLic.Select(0, 0);

            _chkAcceptLicense = new CheckBox();
            _chkAcceptLicense.UseMnemonic = false;
            _chkAcceptLicense.Text = "I accept the terms of the MIT License Agreement";
            _chkAcceptLicense.Checked = true;
            _chkAcceptLicense.ForeColor = TextPrimary;
            _chkAcceptLicense.Font = new Font("Segoe UI Semibold", 9.2F);
            _chkAcceptLicense.Location = new Point(2, 336);
            _chkAcceptLicense.AutoSize = true;
            _chkAcceptLicense.CheckedChanged += delegate
            {
                if (_pageIndex == 0) _btnNext.Enabled = _chkAcceptLicense.Checked;
            };

            Shown += delegate
            {
                txtLic.Select(0, 0);
                _btnNext.Focus();
            };

            p.Controls.Add(title);
            p.Controls.Add(sub);
            p.Controls.Add(card);
            p.Controls.Add(lblLic);
            p.Controls.Add(txtLic);
            p.Controls.Add(_chkAcceptLicense);
            return p;
        }

        private Control MakeFeatureRow(string icon, string title, string desc, int x, int y)
        {
            var pnl = new Panel();
            pnl.Location = new Point(x, y);
            pnl.Size = new Size(500, 24);
            pnl.BackColor = Color.Transparent;

            var lblIcon = new Label();
            lblIcon.Text = icon;
            lblIcon.Font = new Font("Segoe UI", 9F);
            lblIcon.ForeColor = AccentCyan;
            lblIcon.Location = new Point(0, 1);
            lblIcon.Size = new Size(20, 20);

            var lblText = new Label();
            lblText.UseMnemonic = false;
            lblText.Text = title + "  —  " + desc;
            lblText.Font = new Font("Segoe UI", 8.8F);
            lblText.ForeColor = TextPrimary;
            lblText.Location = new Point(22, 1);
            lblText.Size = new Size(478, 20);
            lblText.AutoEllipsis = true;

            pnl.Controls.Add(lblIcon);
            pnl.Controls.Add(lblText);
            return pnl;
        }

        private Panel BuildOptionsPage()
        {
            var p = new Panel();
            var title = MakeHeaderLabel("Customize Setup & Integrations", 0, 0);
            var sub = MakeSubLabel("Choose installation folder and configure system integration components.", 0, 32, 528, 22);

            var lblDir = new Label();
            lblDir.Text = "Destination Folder";
            lblDir.ForeColor = TextMuted;
            lblDir.Font = new Font("Segoe UI Semibold", 8.8F);
            lblDir.Location = new Point(0, 60);
            lblDir.AutoSize = true;

            _txtDir = new TextBox();
            _txtDir.Text = _opts.InstallDir;
            _txtDir.BackColor = BgInput;
            _txtDir.ForeColor = TextPrimary;
            _txtDir.BorderStyle = BorderStyle.FixedSingle;
            _txtDir.Font = new Font("Segoe UI", 9.5F);
            _txtDir.Location = new Point(0, 82);
            _txtDir.Size = new Size(424, 26);

            var btnBrowse = MakeButton("Browse...", false);
            btnBrowse.Size = new Size(96, 26);
            btnBrowse.Location = new Point(432, 81);
            btnBrowse.Click += delegate
            {
                using (var dlg = new FolderBrowserDialog())
                {
                    dlg.Description = "Select Aerix installation folder";
                    dlg.SelectedPath = _txtDir.Text;
                    if (dlg.ShowDialog(this) == DialogResult.OK && !string.IsNullOrWhiteSpace(dlg.SelectedPath))
                    {
                        _txtDir.Text = dlg.SelectedPath;
                    }
                }
            };

            // Options Card
            var cardOpts = MakeCard(0, 118, 528, 148);
            _chkEnv = MakeOptionCheck("Configure AERIX_HOME, stdlib/modules and add bin\\ to User PATH", _opts.ConfigureEnv, 14, 12);
            _chkAssoc = MakeOptionCheck("Register .arx file associations & Explorer context actions (Open / Run / Build)", _opts.FileAssociations, 14, 44);
            _chkIdes = MakeOptionCheck("Automatically install Aerix Language Server (LSP) into detected IDEs", _opts.InstallIdeExtensions, 14, 76);
            _chkSmoke = MakeOptionCheck("Verify compiler with an instant native compile-and-run smoke test", _opts.RunSmokeTest, 14, 108);

            cardOpts.Controls.Add(_chkEnv);
            cardOpts.Controls.Add(_chkAssoc);
            cardOpts.Controls.Add(_chkIdes);
            cardOpts.Controls.Add(_chkSmoke);

            // Detected IDEs Card
            var cardIdes = MakeCard(0, 276, 528, 88);
            var lblEdHdr = new Label();
            lblEdHdr.Text = "Detected Editors on this computer:";
            lblEdHdr.ForeColor = TextMuted;
            lblEdHdr.Font = new Font("Segoe UI Semibold", 8.6F);
            lblEdHdr.Location = new Point(14, 10);
            lblEdHdr.AutoSize = true;
            cardIdes.Controls.Add(lblEdHdr);

            int cx = 14;
            int cy = 36;
            int foundCount = 0;
            foreach (EditorInfo ed in _editors)
            {
                if (!ed.IsDetected) continue;
                foundCount++;
                var pill = new Label();
                pill.Text = "✓ " + ed.Name;
                pill.BackColor = Color.FromArgb(14, 52, 44);
                pill.ForeColor = AccentGreen;
                pill.Font = new Font("Segoe UI Semibold", 8.4F);
                pill.Padding = new Padding(8, 4, 8, 4);
                pill.AutoSize = true;
                pill.Location = new Point(cx, cy);
                cardIdes.Controls.Add(pill);
                cx += pill.PreferredWidth + 8;
                if (cx > 410) { cx = 14; cy += 28; }
            }
            if (foundCount == 0)
            {
                var lblNone = new Label();
                lblNone.Text = "No IDEs detected automatically (VSIX package will be ready in editors\\ folder).";
                lblNone.ForeColor = TextMuted;
                lblNone.Font = new Font("Segoe UI", 8.5F);
                lblNone.Location = new Point(14, 38);
                lblNone.Size = new Size(500, 36);
                cardIdes.Controls.Add(lblNone);
            }

            p.Controls.Add(title);
            p.Controls.Add(sub);
            p.Controls.Add(lblDir);
            p.Controls.Add(_txtDir);
            p.Controls.Add(btnBrowse);
            p.Controls.Add(cardOpts);
            p.Controls.Add(cardIdes);
            return p;
        }

        private Panel BuildProgressPage()
        {
            var p = new Panel();
            var title = MakeHeaderLabel("Installing Aerix " + _version, 0, 0);

            _lblProgTitle = new Label();
            _lblProgTitle.Text = "Preparing installation...";
            _lblProgTitle.ForeColor = TextMuted;
            _lblProgTitle.Font = new Font("Segoe UI", 9.5F);
            _lblProgTitle.Location = new Point(0, 42);
            _lblProgTitle.Size = new Size(450, 22);

            _lblProgPct = new Label();
            _lblProgPct.Text = "0%";
            _lblProgPct.ForeColor = AccentCyan;
            _lblProgPct.Font = new Font("Segoe UI", 11F, FontStyle.Bold);
            _lblProgPct.Location = new Point(458, 40);
            _lblProgPct.Size = new Size(70, 24);
            _lblProgPct.TextAlign = ContentAlignment.MiddleRight;

            _progressBar = new AerixProgressBar();
            _progressBar.Location = new Point(0, 72);
            _progressBar.Size = new Size(528, 16);

            _txtLog = new TextBox();
            _txtLog.Multiline = true;
            _txtLog.ReadOnly = true;
            _txtLog.ScrollBars = ScrollBars.Vertical;
            _txtLog.BackColor = BgInput;
            _txtLog.ForeColor = Color.FromArgb(170, 192, 224);
            _txtLog.BorderStyle = BorderStyle.FixedSingle;
            _txtLog.Font = new Font("Consolas", 8.4F);
            _txtLog.Location = new Point(0, 102);
            _txtLog.Size = new Size(528, 268);

            p.Controls.Add(title);
            p.Controls.Add(_lblProgTitle);
            p.Controls.Add(_lblProgPct);
            p.Controls.Add(_progressBar);
            p.Controls.Add(_txtLog);
            return p;
        }

        private Panel BuildFinishPage()
        {
            var p = new Panel();
            _lblFinishHeadline = MakeHeaderLabel("Aerix " + _version + " is Ready to Code!", 0, 6);
            _lblFinishHeadline.ForeColor = AccentGreen;

            var sub = MakeSubLabel("All toolchain binaries, standard libraries, and IDE extensions have been set up.", 0, 36, 528, 22);

            var card = MakeCard(0, 68, 528, 206);
            _lblFinishBody = new Label();
            _lblFinishBody.ForeColor = TextPrimary;
            _lblFinishBody.Font = new Font("Segoe UI", 9.5F);
            _lblFinishBody.Location = new Point(18, 16);
            _lblFinishBody.Size = new Size(492, 174);
            card.Controls.Add(_lblFinishBody);

            _btnVerifyTerminal = MakeButton("Open Terminal & Test arx", true);
            _btnVerifyTerminal.Size = new Size(220, 36);
            _btnVerifyTerminal.Location = new Point(0, 286);
            _btnVerifyTerminal.Click += delegate
            {
                try
                {
                    string arxExe = Path.Combine(_opts.InstallDir, "bin", "arx.exe");
                    Process.Start("cmd.exe", string.Format("/K \"\"{0}\" version\"", arxExe));
                }
                catch { }
            };

            var lblTip = new Label();
            lblTip.Text = "💡 Tip: If VS Code or Antigravity is open, run 'Developer: Reload Window' to connect to the updated LSP.";
            lblTip.ForeColor = TextMuted;
            lblTip.Font = new Font("Segoe UI", 8.6F);
            lblTip.Location = new Point(0, 332);
            lblTip.Size = new Size(528, 32);

            p.Controls.Add(_lblFinishHeadline);
            p.Controls.Add(sub);
            p.Controls.Add(card);
            p.Controls.Add(_btnVerifyTerminal);
            p.Controls.Add(lblTip);
            return p;
        }

        private void BuildUninstallView()
        {
            string detected = InstallerEngine.ResolveInstalledDirFromRegistry();
            if (string.IsNullOrWhiteSpace(detected))
            {
                string selfExe = Assembly.GetExecutingAssembly().Location;
                detected = string.IsNullOrEmpty(selfExe) ? InstallerEngine.GetDefaultInstallDir() : Path.GetDirectoryName(selfExe);
            }
            _opts.InstallDir = detected;

            var title = MakeHeaderLabel("Uninstall Aerix " + _version, 0, 0);
            var sub = MakeSubLabel(
                "Completely remove Aerix compiler, standard library, and system integrations.",
                0, 32, 528, 22);

            // Warning / Impact Scope Card (122px)
            var cardScope = MakeCard(0, 58, 528, 122);

            var lblWarn = new Label();
            lblWarn.UseMnemonic = false;
            lblWarn.Text = "⚠️  The following components will be removed from your PC:";
            lblWarn.ForeColor = Color.FromArgb(252, 211, 77); // Amber-300
            lblWarn.Font = new Font("Segoe UI Semibold", 8.8F);
            lblWarn.Location = new Point(14, 10);
            lblWarn.AutoSize = true;
            cardScope.Controls.Add(lblWarn);

            var row1 = MakeFeatureRow("🗑️", "Compiler Toolchain", "Executables (arx.exe, arxc.exe), tools, and C99 seeds.", 14, 34);
            var row2 = MakeFeatureRow("⚙️", "Environment & PATH", "System AERIX_HOME, AERIX_STDLIB, and %PATH% entries.", 14, 62);
            var row3 = MakeFeatureRow("📄", "File Associations", ".arx source file types, context menus, and registry keys.", 14, 90);

            cardScope.Controls.Add(row1);
            cardScope.Controls.Add(row2);
            cardScope.Controls.Add(row3);

            // Install Directory Card (64px)
            var cardDir = MakeCard(0, 190, 528, 64);
            var lblDirHdr = new Label();
            lblDirHdr.UseMnemonic = false;
            lblDirHdr.Text = "Installation Directory to Remove:";
            lblDirHdr.ForeColor = TextMuted;
            lblDirHdr.Font = new Font("Segoe UI Semibold", 8.6F);
            lblDirHdr.Location = new Point(14, 9);
            lblDirHdr.AutoSize = true;
            cardDir.Controls.Add(lblDirHdr);

            var lblPath = new Label();
            lblPath.UseMnemonic = false;
            lblPath.Text = "📁  " + _opts.InstallDir;
            lblPath.ForeColor = AccentCyan;
            lblPath.Font = new Font("Segoe UI Semibold", 9.8F);
            lblPath.Location = new Point(14, 31);
            lblPath.Size = new Size(500, 24);
            cardDir.Controls.Add(lblPath);

            // Progress & Status Section
            _lblUninstStatus = new Label();
            _lblUninstStatus.UseMnemonic = false;
            _lblUninstStatus.Text = "Ready. Click 'Uninstall' to proceed.";
            _lblUninstStatus.ForeColor = TextPrimary;
            _lblUninstStatus.Font = new Font("Segoe UI Semibold", 9.2F);
            _lblUninstStatus.Location = new Point(0, 266);
            _lblUninstStatus.Size = new Size(528, 22);

            _uninstProgress = new AerixProgressBar();
            _uninstProgress.Location = new Point(0, 292);
            _uninstProgress.Size = new Size(528, 18);

            _lblUninstNote = new Label();
            _lblUninstNote.UseMnemonic = false;
            _lblUninstNote.Text = "💡 Tip: Any user projects or custom .arx files outside " + _opts.InstallDir + " will remain untouched.";
            _lblUninstNote.ForeColor = TextMuted;
            _lblUninstNote.Font = new Font("Segoe UI", 8.6F);
            _lblUninstNote.Location = new Point(0, 320);
            _lblUninstNote.Size = new Size(528, 36);

            _contentHost.Controls.Add(title);
            _contentHost.Controls.Add(sub);
            _contentHost.Controls.Add(cardScope);
            _contentHost.Controls.Add(cardDir);
            _contentHost.Controls.Add(_lblUninstStatus);
            _contentHost.Controls.Add(_uninstProgress);
            _contentHost.Controls.Add(_lblUninstNote);

            _btnUninstRun = MakeButton("Uninstall", true);
            _btnUninstRun.BackColor = AccentDanger;
            _btnUninstRun.ForeColor = Color.White;
            _btnUninstRun.FlatAppearance.MouseOverBackColor = Color.FromArgb(248, 113, 113);
            _btnUninstRun.Location = new Point(_footer.Width - 216, 12);
            _btnUninstRun.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _btnUninstRun.Click += OnStartUninstall;

            _btnUninstClose = MakeButton("Cancel", false);
            _btnUninstClose.Location = new Point(_footer.Width - 110, 12);
            _btnUninstClose.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _btnUninstClose.Click += delegate
            {
                if (_isBusy) return;
                if (_uninstDone) InstallerEngine.ScheduleSelfDeleteIfRunningFrom(_opts.InstallDir);
                Close();
            };

            _footer.Controls.Add(_btnUninstRun);
            _footer.Controls.Add(_btnUninstClose);
        }


    }
}
