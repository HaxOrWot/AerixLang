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
    public sealed class SetupForm : Form
    {
        // Theme palette (Deep Obsidian + Aerix Cyan)
        private static readonly Color BgWindow = Color.FromArgb(18, 27, 46);      // #121B2E
        private static readonly Color BgSidebar = Color.FromArgb(13, 20, 34);     // #0D1422
        private static readonly Color BgHeader = Color.FromArgb(11, 16, 28);      // #0B101C
        private static readonly Color BgCard = Color.FromArgb(23, 34, 59);        // #17223B
        private static readonly Color BgInput = Color.FromArgb(10, 16, 28);       // #0A101C
        private static readonly Color BorderSubtle = Color.FromArgb(36, 52, 82);  // #243452
        private static readonly Color TextPrimary = Color.FromArgb(235, 242, 252);
        private static readonly Color TextMuted = Color.FromArgb(142, 160, 189);
        private static readonly Color AccentCyan = Color.FromArgb(0, 220, 255);   // #00DCFF
        private static readonly Color AccentBlue = Color.FromArgb(56, 139, 253);
        private static readonly Color AccentGreen = Color.FromArgb(34, 211, 153);
        private static readonly Color AccentDanger = Color.FromArgb(244, 91, 105);

        private readonly bool _uninstallMode;
        private readonly InstallOptions _opts;
        private readonly string _version;
        private readonly List<EditorInfo> _editors;

        private Panel _sidebar;
        private Panel _contentHost;
        private Panel _footer;
        private Button _btnBack;
        private Button _btnNext;
        private Button _btnCancel;

        private Panel[] _pages;
        private int _pageIndex = 0;
        private bool _isBusy = false;
        private bool _dragActive = false;
        private Point _dragOffset;

        // Controls across pages
        private CheckBox _chkAcceptLicense;
        private TextBox _txtDir;
        private CheckBox _chkEnv;
        private CheckBox _chkAssoc;
        private CheckBox _chkIdes;
        private CheckBox _chkSmoke;

        private AerixProgressBar _progressBar;
        private Label _lblProgTitle;
        private Label _lblProgPct;
        private TextBox _txtLog;

        private Label _lblFinishHeadline;
        private Label _lblFinishBody;
        private Button _btnVerifyTerminal;

        // Uninstall controls
        private Label _lblUninstInfo;
        private AerixProgressBar _uninstProgress;
        private Label _lblUninstStatus;
        private Button _btnUninstRun;
        private Button _btnUninstClose;
        private bool _uninstDone = false;

        private Image _brandImg;

        public SetupForm(bool uninstallMode, InstallOptions initialOpts)
        {
            _uninstallMode = uninstallMode;
            _opts = initialOpts ?? new InstallOptions();
            _version = InstallerEngine.GetVersion();
            _editors = InstallerEngine.DetectEditors();

            SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint, true);
            AutoScaleMode = AutoScaleMode.Dpi;
            AutoScaleDimensions = new SizeF(96F, 96F);
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new Size(780, 510);
            BackColor = BgWindow;
            ForeColor = TextPrimary;
            Font = new Font("Segoe UI", 9.5F, FontStyle.Regular);
            Text = "Aerix " + _version + " Setup";

            LoadEmbeddedIcon();
            BuildChrome();
            if (_uninstallMode)
            {
                BuildUninstallView();
            }
            else
            {
                BuildWizardPages();
                ShowPage(0);
            }
        }

        protected override CreateParams CreateParams
        {
            get
            {
                CreateParams cp = base.CreateParams;
                cp.ClassStyle |= 0x00020000; // CS_DROPSHADOW
                return cp;
            }
        }

        private void LoadEmbeddedIcon()
        {
            try
            {
                string selfExe = Assembly.GetExecutingAssembly().Location;
                if (!string.IsNullOrEmpty(selfExe) && File.Exists(selfExe))
                {
                    this.Icon = Icon.ExtractAssociatedIcon(selfExe);
                }
            }
            catch
            {
            }

            try
            {
                byte[] pngBytes = InstallerEngine.ReadEmbeddedBytes("aerix-icon.png");
                if (pngBytes != null && pngBytes.Length > 0)
                {
                    using (var ms = new MemoryStream(pngBytes))
                    using (var raw = Image.FromStream(ms))
                    {
                        _brandImg = new Bitmap(raw);
                    }
                }
            }
            catch
            {
            }
        }

        private void BuildChrome()
        {
            // Top accent line (2px cyan)
            var topAccent = new Panel();
            topAccent.Dock = DockStyle.Top;
            topAccent.Width = ClientSize.Width;
            topAccent.Height = 2;
            topAccent.BackColor = AccentCyan;

            // Title Bar (36px)
            var titleBar = new Panel();
            titleBar.Dock = DockStyle.Top;
            titleBar.Width = ClientSize.Width;
            titleBar.Height = 36;
            titleBar.BackColor = BgHeader;
            titleBar.MouseDown += OnHeaderMouseDown;
            titleBar.MouseMove += OnHeaderMouseMove;
            titleBar.MouseUp += OnHeaderMouseUp;

            var lblTitle = new Label();
            lblTitle.Text = _uninstallMode
                ? "Aerix " + _version + "  —  Uninstall"
                : "Aerix " + _version + "  —  Windows Setup";
            lblTitle.ForeColor = TextMuted;
            lblTitle.Font = new Font("Segoe UI Semibold", 9.2F);
            lblTitle.UseMnemonic = false;
            lblTitle.AutoSize = false;
            lblTitle.Size = new Size(520, 36);
            lblTitle.Location = new Point(16, 0);
            lblTitle.TextAlign = ContentAlignment.MiddleLeft;
            lblTitle.MouseDown += OnHeaderMouseDown;
            lblTitle.MouseMove += OnHeaderMouseMove;
            lblTitle.MouseUp += OnHeaderMouseUp;

            var btnClose = CreateTitleButton("×", new Point(titleBar.Width - 40, 0), true);
            btnClose.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            btnClose.Click += delegate
            {
                if (!_isBusy) Close();
            };

            var btnMin = CreateTitleButton("—", new Point(titleBar.Width - 80, 0), false);
            btnMin.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            btnMin.Click += delegate
            {
                WindowState = FormWindowState.Minimized;
            };

            titleBar.Controls.Add(lblTitle);
            titleBar.Controls.Add(btnMin);
            titleBar.Controls.Add(btnClose);

            // Left Sidebar (216px)
            _sidebar = new Panel();
            _sidebar.Dock = DockStyle.Left;
            _sidebar.Width = 216;
            _sidebar.BackColor = BgSidebar;
            _sidebar.Paint += PaintSidebar;

            // Footer Bar (58px)
            _footer = new Panel();
            _footer.Dock = DockStyle.Bottom;
            _footer.Width = ClientSize.Width;
            _footer.Height = 58;
            _footer.BackColor = BgHeader;
            _footer.Paint += delegate(object s, PaintEventArgs e)
            {
                using (var pen = new Pen(BorderSubtle, 1))
                {
                    e.Graphics.DrawLine(pen, 0, 0, _footer.Width, 0);
                }
            };

            _contentHost = new Panel();
            _contentHost.Dock = DockStyle.Fill;
            _contentHost.BackColor = BgWindow;
            _contentHost.Padding = new Padding(26, 20, 26, 16);

            Controls.Add(_contentHost);
            Controls.Add(_footer);
            if (!_uninstallMode) Controls.Add(_sidebar);
            Controls.Add(titleBar);
            Controls.Add(topAccent);
        }

        private Button CreateTitleButton(string txt, Point loc, bool isClose)
        {
            var b = new Button();
            b.Text = txt;
            b.FlatStyle = FlatStyle.Flat;
            b.FlatAppearance.BorderSize = 0;
            b.FlatAppearance.MouseOverBackColor = isClose ? Color.FromArgb(196, 43, 28) : Color.FromArgb(30, 44, 72);
            b.BackColor = BgHeader;
            b.ForeColor = TextMuted;
            b.Font = new Font("Segoe UI", 10.5F);
            b.Size = new Size(40, 36);
            b.Location = loc;
            b.Cursor = Cursors.Hand;
            b.TabStop = false;
            b.MouseEnter += delegate { b.ForeColor = Color.White; };
            b.MouseLeave += delegate { b.ForeColor = TextMuted; };
            return b;
        }

        private void PaintSidebar(object sender, PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;

            // Right divider
            using (var pen = new Pen(BorderSubtle, 1))
            {
                g.DrawLine(pen, _sidebar.Width - 1, 0, _sidebar.Width - 1, _sidebar.Height);
            }

            // Brand badge
            if (_brandImg != null)
            {
                g.DrawImage(_brandImg, new Rectangle(22, 22, 36, 36));
            }
            using (var fBrand = new Font("Segoe UI", 14F, FontStyle.Bold))
            using (var bTitle = new SolidBrush(TextPrimary))
            {
                g.DrawString("AERIX", fBrand, bTitle, new PointF(66, 20));
            }
            using (var fVer = new Font("Segoe UI Semibold", 8.2F))
            using (var bCyan = new SolidBrush(AccentCyan))
            {
                g.DrawString("v" + _version, fVer, bCyan, new PointF(67, 45));
            }

            // Stepper items
            string[] steps = { "Welcome & License", "Setup & Editors", "Installing", "Ready to Code" };
            int y = 104;
            for (int i = 0; i < steps.Length; i++)
            {
                bool active = (i == _pageIndex);
                bool done = (i < _pageIndex);

                if (i < steps.Length - 1)
                {
                    using (var penLine = new Pen(done ? AccentGreen : BorderSubtle, 2))
                    {
                        g.DrawLine(penLine, 34, y + 22, 34, y + 48);
                    }
                }

                Rectangle circle = new Rectangle(23, y, 22, 22);
                Color fill = active ? AccentCyan : (done ? AccentGreen : Color.FromArgb(24, 36, 62));
                using (var brFill = new SolidBrush(fill))
                {
                    g.FillEllipse(brFill, circle);
                }
                if (!active && !done)
                {
                    using (var penC = new Pen(BorderSubtle, 1.5F))
                    {
                        g.DrawEllipse(penC, circle);
                    }
                }

                string badgeTxt = done ? "✓" : (i + 1).ToString();
                Color badgeFg = (active || done) ? BgHeader : TextMuted;
                using (var fNum = new Font("Segoe UI", 8.5F, FontStyle.Bold))
                using (var bNum = new SolidBrush(badgeFg))
                {
                    var sf = new StringFormat();
                    sf.Alignment = StringAlignment.Center;
                    sf.LineAlignment = StringAlignment.Center;
                    g.DrawString(badgeTxt, fNum, bNum, new RectangleF(circle.X, circle.Y + 0.5F, circle.Width, circle.Height), sf);
                }

                using (var fStep = new Font("Segoe UI", 9.5F, active ? FontStyle.Bold : FontStyle.Regular))
                using (var bStep = new SolidBrush(active ? TextPrimary : (done ? AccentGreen : TextMuted)))
                {
                    g.DrawString(steps[i], fStep, bStep, new PointF(56, y + 2));
                }

                y += 52;
            }

            // Bottom subtle architecture tag
            using (var fNote = new Font("Segoe UI", 8F))
            using (var bNote = new SolidBrush(Color.FromArgb(100, 118, 148)))
            {
                g.DrawString("Native PE32+ x86-64\r\nZero External Dependencies", fNote, bNote, new PointF(22, _sidebar.Height - 48));
            }
        }

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

            // Footer buttons
            _btnBack = MakeButton("< Back", false);
            _btnBack.Location = new Point(_footer.Width - 310, 12);
            _btnBack.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            _btnBack.Click += delegate { if (_pageIndex == 1) ShowPage(0); };

            _btnNext = MakeButton("Next >", true);
            _btnNext.Location = new Point(_footer.Width - 210, 12);
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
                "Sets up the self-hosting native x86-64 Aerix compiler, standard runtime, language modules, LSP editor integration (highlighting, hover & F12 navigation), and system PATH.",
                0, 32, 508, 40);

            var card = MakeCard(0, 82, 508, 90);
            var bullets = new Label();
            bullets.UseMnemonic = false;
            bullets.Text =
                "• Native PE32+ compiler (arx.exe, arxc.exe) — zero GCC required at runtime\r\n" +
                "• Stdlib & modules (aerix_rt.h, Math, Random) + .arx Explorer file icons\r\n" +
                "• Compiler LSP extension v" + _version + " auto-installed for detected IDEs";
            bullets.ForeColor = TextPrimary;
            bullets.Font = new Font("Segoe UI", 9.0F);
            bullets.Location = new Point(14, 12);
            bullets.Size = new Size(480, 66);
            card.Controls.Add(bullets);

            var lblLic = new Label();
            lblLic.UseMnemonic = false;
            lblLic.Text = "License Agreement (MIT)";
            lblLic.ForeColor = TextMuted;
            lblLic.Font = new Font("Segoe UI Semibold", 8.8F);
            lblLic.Location = new Point(0, 182);
            lblLic.AutoSize = true;

            var txtLic = new TextBox();
            txtLic.Multiline = true;
            txtLic.ReadOnly = true;
            txtLic.TabStop = false;
            txtLic.ScrollBars = ScrollBars.Vertical;
            txtLic.BackColor = BgInput;
            txtLic.ForeColor = TextMuted;
            txtLic.BorderStyle = BorderStyle.FixedSingle;
            txtLic.Font = new Font("Consolas", 8.3F);
            txtLic.Location = new Point(0, 204);
            txtLic.Size = new Size(508, 134);
            txtLic.Text = InstallerEngine.GetLicenseText();
            txtLic.Select(0, 0);

            _chkAcceptLicense = new CheckBox();
            _chkAcceptLicense.UseMnemonic = false;
            _chkAcceptLicense.Text = "I accept the terms of the MIT License Agreement";
            _chkAcceptLicense.Checked = true;
            _chkAcceptLicense.ForeColor = TextPrimary;
            _chkAcceptLicense.Font = new Font("Segoe UI Semibold", 9.2F);
            _chkAcceptLicense.Location = new Point(2, 348);
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

        private Panel BuildOptionsPage()
        {
            var p = new Panel();
            var title = MakeHeaderLabel("Customize Setup & Detected IDEs", 0, 0);
            var sub = MakeSubLabel("Choose your install folder and integration features for this Windows user.", 0, 32, 505, 22);

            var lblDir = new Label();
            lblDir.Text = "Destination Folder";
            lblDir.ForeColor = TextMuted;
            lblDir.Font = new Font("Segoe UI Semibold", 8.8F);
            lblDir.Location = new Point(0, 62);
            lblDir.AutoSize = true;

            _txtDir = new TextBox();
            _txtDir.Text = _opts.InstallDir;
            _txtDir.BackColor = BgInput;
            _txtDir.ForeColor = TextPrimary;
            _txtDir.BorderStyle = BorderStyle.FixedSingle;
            _txtDir.Font = new Font("Segoe UI", 9.5F);
            _txtDir.Location = new Point(0, 84);
            _txtDir.Size = new Size(412, 26);

            var btnBrowse = MakeButton("Browse...", false);
            btnBrowse.Size = new Size(88, 26);
            btnBrowse.Location = new Point(420, 83);
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

            var cardOpts = MakeCard(0, 122, 508, 152);
            _chkEnv = MakeOptionCheck("Configure AERIX_HOME, stdlib/modules env vars & add bin to User PATH", _opts.ConfigureEnv, 14, 12);
            _chkAssoc = MakeOptionCheck("Register .arx file icon & Explorer right-click actions (Open / Run / Build)", _opts.FileAssociations, 14, 44);
            _chkIdes = MakeOptionCheck("Install Aerix v" + _version + " LSP Extension into all detected IDEs", _opts.InstallIdeExtensions, 14, 76);
            _chkSmoke = MakeOptionCheck("Verify toolchain with a quick native compile & run smoke test", _opts.RunSmokeTest, 14, 108);
            cardOpts.Controls.Add(_chkEnv);
            cardOpts.Controls.Add(_chkAssoc);
            cardOpts.Controls.Add(_chkIdes);
            cardOpts.Controls.Add(_chkSmoke);

            // Detected IDE chips card
            var cardIdes = MakeCard(0, 286, 508, 92);
            var lblEdHdr = new Label();
            lblEdHdr.Text = "Detected Editors on this PC:";
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
                pill.BackColor = Color.FromArgb(16, 62, 56);
                pill.ForeColor = AccentGreen;
                pill.Font = new Font("Segoe UI Semibold", 8.4F);
                pill.Padding = new Padding(8, 4, 8, 4);
                pill.AutoSize = true;
                pill.Location = new Point(cx, cy);
                cardIdes.Controls.Add(pill);
                cx += pill.PreferredWidth + 8;
                if (cx > 390) { cx = 14; cy += 28; }
            }
            if (foundCount == 0)
            {
                var lblNone = new Label();
                lblNone.Text = "No VS Code / Antigravity / Cursor installs found automatically (VSIX will still be staged in editors\\).";
                lblNone.ForeColor = TextMuted;
                lblNone.Font = new Font("Segoe UI", 8.5F);
                lblNone.Location = new Point(14, 38);
                lblNone.Size = new Size(480, 38);
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
            _lblProgTitle.Size = new Size(430, 22);

            _lblProgPct = new Label();
            _lblProgPct.Text = "0%";
            _lblProgPct.ForeColor = AccentCyan;
            _lblProgPct.Font = new Font("Segoe UI", 10.5F, FontStyle.Bold);
            _lblProgPct.Location = new Point(442, 40);
            _lblProgPct.Size = new Size(66, 24);
            _lblProgPct.TextAlign = ContentAlignment.MiddleRight;

            _progressBar = new AerixProgressBar();
            _progressBar.Location = new Point(0, 72);
            _progressBar.Size = new Size(508, 16);

            _txtLog = new TextBox();
            _txtLog.Multiline = true;
            _txtLog.ReadOnly = true;
            _txtLog.ScrollBars = ScrollBars.Vertical;
            _txtLog.BackColor = BgInput;
            _txtLog.ForeColor = Color.FromArgb(170, 192, 224);
            _txtLog.BorderStyle = BorderStyle.FixedSingle;
            _txtLog.Font = new Font("Consolas", 8.4F);
            _txtLog.Location = new Point(0, 102);
            _txtLog.Size = new Size(508, 276);

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
            _lblFinishHeadline = MakeHeaderLabel("Aerix " + _version + " is Ready!", 0, 8);
            _lblFinishHeadline.ForeColor = AccentGreen;

            var card = MakeCard(0, 52, 508, 226);
            _lblFinishBody = new Label();
            _lblFinishBody.ForeColor = TextPrimary;
            _lblFinishBody.Font = new Font("Segoe UI", 9.5F);
            _lblFinishBody.Location = new Point(16, 16);
            _lblFinishBody.Size = new Size(476, 196);
            card.Controls.Add(_lblFinishBody);

            _btnVerifyTerminal = MakeButton("Open Terminal & Run arx version", false);
            _btnVerifyTerminal.Size = new Size(248, 36);
            _btnVerifyTerminal.Location = new Point(0, 294);
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
            lblTip.Text = "Tip: If VS Code or Antigravity is currently open, run 'Developer: Reload Window' (Ctrl+Shift+P) to start the updated v" + _version + " LSP server.";
            lblTip.ForeColor = TextMuted;
            lblTip.Font = new Font("Segoe UI", 8.6F);
            lblTip.Location = new Point(0, 342);
            lblTip.Size = new Size(508, 36);

            p.Controls.Add(_lblFinishHeadline);
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

            var title = MakeHeaderLabel("Uninstall Aerix " + _version, 0, 6);
            _lblUninstInfo = new Label();
            _lblUninstInfo.Text = "This will remove Aerix binaries, environment variables, PATH entries, .arx file associations, and registry records from:\r\n\r\n" + _opts.InstallDir;
            _lblUninstInfo.ForeColor = TextPrimary;
            _lblUninstInfo.Font = new Font("Segoe UI", 9.6F);
            _lblUninstInfo.Location = new Point(0, 50);
            _lblUninstInfo.Size = new Size(720, 90);

            _lblUninstStatus = new Label();
            _lblUninstStatus.Text = "Click Uninstall to proceed.";
            _lblUninstStatus.ForeColor = TextMuted;
            _lblUninstStatus.Location = new Point(0, 160);
            _lblUninstStatus.Size = new Size(720, 24);

            _uninstProgress = new AerixProgressBar();
            _uninstProgress.Location = new Point(0, 192);
            _uninstProgress.Size = new Size(724, 16);

            _contentHost.Controls.Add(title);
            _contentHost.Controls.Add(_lblUninstInfo);
            _contentHost.Controls.Add(_lblUninstStatus);
            _contentHost.Controls.Add(_uninstProgress);

            _btnUninstRun = MakeButton("Uninstall", true);
            _btnUninstRun.BackColor = AccentDanger;
            _btnUninstRun.ForeColor = Color.White;
            _btnUninstRun.FlatAppearance.MouseOverBackColor = Color.FromArgb(255, 110, 122);
            _btnUninstRun.Location = new Point(_footer.Width - 210, 12);
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

        private void OnStartUninstall(object sender, EventArgs e)
        {
            if (_isBusy) return;
            _isBusy = true;
            _btnUninstRun.Enabled = false;
            _btnUninstClose.Enabled = false;

            var t = new Thread(delegate()
            {
                string err;
                bool ok = InstallerEngine.RunUninstall(_opts.InstallDir, delegate(int pct, string status, string logLine)
                {
                    BeginInvoke((MethodInvoker)delegate
                    {
                        _uninstProgress.Value = pct;
                        _lblUninstStatus.Text = status;
                    });
                }, out err);

                BeginInvoke((MethodInvoker)delegate
                {
                    _isBusy = false;
                    _uninstDone = ok;
                    _btnUninstClose.Text = "Close";
                    _btnUninstClose.Enabled = true;
                    if (!ok)
                    {
                        _lblUninstStatus.ForeColor = AccentDanger;
                        _lblUninstStatus.Text = "Uninstall failed: " + err;
                    }
                    else
                    {
                        _lblUninstStatus.ForeColor = AccentGreen;
                        _lblUninstStatus.Text = "Aerix has been cleanly uninstalled.";
                    }
                });
            });
            t.IsBackground = true;
            t.Start();
        }

        private void ShowPage(int idx)
        {
            _pageIndex = idx;
            for (int i = 0; i < _pages.Length; i++)
            {
                _pages[i].Visible = (i == idx);
            }
            _btnBack.Visible = (idx == 1);
            _btnCancel.Visible = (idx < 3);
            _btnNext.Visible = true;

            if (idx == 0)
            {
                _btnNext.Text = "Next >";
                _btnNext.Enabled = _chkAcceptLicense.Checked;
            }
            else if (idx == 1)
            {
                _btnNext.Text = "Install";
                _btnNext.Enabled = true;
            }
            else if (idx == 2)
            {
                _btnNext.Text = "Installing...";
                _btnNext.Enabled = false;
                _btnCancel.Enabled = false;
            }
            else if (idx == 3)
            {
                _btnNext.Text = "Finish";
                _btnNext.Enabled = true;
            }
            _sidebar.Invalidate();
        }

        private void OnNextClicked(object sender, EventArgs e)
        {
            if (_pageIndex == 0)
            {
                ShowPage(1);
                return;
            }
            if (_pageIndex == 1)
            {
                string target = _txtDir.Text.Trim();
                if (string.IsNullOrEmpty(target))
                {
                    MessageBox.Show(this, "Please select a valid installation directory.", "Aerix Setup", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }
                _opts.InstallDir = target;
                _opts.ConfigureEnv = _chkEnv.Checked;
                _opts.FileAssociations = _chkAssoc.Checked;
                _opts.InstallIdeExtensions = _chkIdes.Checked;
                _opts.RunSmokeTest = _chkSmoke.Checked;
                BeginInstall();
                return;
            }
            if (_pageIndex == 3)
            {
                Close();
            }
        }

        private void BeginInstall()
        {
            _isBusy = true;
            _txtLog.Clear();
            _progressBar.Value = 0;
            ShowPage(2);

            var t = new Thread(delegate()
            {
                InstallReport rep = InstallerEngine.RunInstall(_opts, delegate(int pct, string status, string logLine)
                {
                    BeginInvoke((MethodInvoker)delegate
                    {
                        _progressBar.Value = pct;
                        _lblProgPct.Text = pct + "%";
                        _lblProgTitle.Text = status;
                        if (!string.IsNullOrEmpty(logLine))
                        {
                            _txtLog.AppendText(logLine + "\r\n");
                        }
                    });
                });

                BeginInvoke((MethodInvoker)delegate
                {
                    _isBusy = false;
                    _btnCancel.Enabled = true;

                    if (rep.Success)
                    {
                        string eds = rep.InstalledEditors.Count > 0 ? string.Join(", ", rep.InstalledEditors.ToArray()) : "None detected (VSIX staged in editors\\)";
                        string smoke = string.IsNullOrEmpty(rep.SmokeTestSummary) ? "Skipped" : rep.SmokeTestSummary;
                        _lblFinishHeadline.Text = "Aerix " + rep.InstalledVersion + " Installed Successfully!";
                        _lblFinishHeadline.ForeColor = AccentGreen;
                        _lblFinishBody.Text = string.Format(
                            "Install Folder:\r\n  {0}\r\n\r\n" +
                            "Files Extracted:  {1}\r\n" +
                            "IDE Extensions:   {2}\r\n" +
                            "Verification:     {3}",
                            _opts.InstallDir, rep.ExtractedFiles, eds, smoke);
                        _btnVerifyTerminal.Visible = true;
                        ShowPage(3);
                    }
                    else
                    {
                        _lblFinishHeadline.Text = "Installation Encountered an Error";
                        _lblFinishHeadline.ForeColor = AccentDanger;
                        _lblFinishBody.Text = rep.ErrorMessage;
                        _btnVerifyTerminal.Visible = false;
                        ShowPage(3);
                    }
                });
            });
            t.IsBackground = true;
            t.Start();
        }

        private Label MakeHeaderLabel(string txt, int x, int y)
        {
            var l = new Label();
            l.UseMnemonic = false;
            l.Text = txt;
            l.ForeColor = TextPrimary;
            l.Font = new Font("Segoe UI", 16F, FontStyle.Bold);
            l.Location = new Point(x, y);
            l.AutoSize = true;
            return l;
        }

        private Label MakeSubLabel(string txt, int x, int y, int w, int h)
        {
            var l = new Label();
            l.UseMnemonic = false;
            l.Text = txt;
            l.ForeColor = TextMuted;
            l.Font = new Font("Segoe UI", 9.2F);
            l.Location = new Point(x, y);
            l.Size = new Size(w, h);
            return l;
        }

        private Panel MakeCard(int x, int y, int w, int h)
        {
            var c = new Panel();
            c.Location = new Point(x, y);
            c.Size = new Size(w, h);
            c.BackColor = BgCard;
            c.Paint += delegate(object s, PaintEventArgs e)
            {
                e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
                using (var pen = new Pen(BorderSubtle, 1))
                {
                    e.Graphics.DrawRectangle(pen, 0, 0, c.Width - 1, c.Height - 1);
                }
            };
            return c;
        }

        private CheckBox MakeOptionCheck(string txt, bool checkedVal, int x, int y)
        {
            var cb = new CheckBox();
            cb.UseMnemonic = false;
            cb.Text = txt;
            cb.Checked = checkedVal;
            cb.ForeColor = TextPrimary;
            cb.Font = new Font("Segoe UI", 9.2F);
            cb.Location = new Point(x, y);
            cb.AutoSize = true;
            return cb;
        }

        private Button MakeButton(string txt, bool primary)
        {
            var b = new Button();
            b.Text = txt;
            b.Size = new Size(92, 34);
            b.FlatStyle = FlatStyle.Flat;
            b.Cursor = Cursors.Hand;
            b.Font = new Font("Segoe UI Semibold", 9.2F);
            if (primary)
            {
                b.BackColor = AccentCyan;
                b.ForeColor = BgHeader;
                b.FlatAppearance.BorderSize = 0;
                b.FlatAppearance.MouseOverBackColor = Color.FromArgb(46, 232, 255);
            }
            else
            {
                b.BackColor = BgCard;
                b.ForeColor = TextPrimary;
                b.FlatAppearance.BorderSize = 1;
                b.FlatAppearance.BorderColor = BorderSubtle;
                b.FlatAppearance.MouseOverBackColor = Color.FromArgb(32, 46, 80);
            }
            return b;
        }

        private void OnHeaderMouseDown(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                _dragActive = true;
                _dragOffset = e.Location;
            }
        }

        private void OnHeaderMouseMove(object sender, MouseEventArgs e)
        {
            if (_dragActive)
            {
                Point screen = ((Control)sender).PointToScreen(e.Location);
                Location = new Point(screen.X - _dragOffset.X, screen.Y - _dragOffset.Y);
            }
        }

        private void OnHeaderMouseUp(object sender, MouseEventArgs e)
        {
            _dragActive = false;
        }

        private sealed class AerixProgressBar : Control
        {
            private int _value = 0;
            public int Value
            {
                get { return _value; }
                set
                {
                    int clamped = Math.Max(0, Math.Min(100, value));
                    if (_value != clamped)
                    {
                        _value = clamped;
                        Invalidate();
                    }
                }
            }

            public AerixProgressBar()
            {
                SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint, true);
            }

            protected override void OnPaint(PaintEventArgs e)
            {
                e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
                Rectangle track = new Rectangle(0, 0, Width - 1, Height - 1);
                using (var bg = new SolidBrush(BgInput))
                using (var pen = new Pen(BorderSubtle, 1))
                {
                    e.Graphics.FillRectangle(bg, track);
                    e.Graphics.DrawRectangle(pen, track);
                }
                if (_value > 0)
                {
                    int fillW = Math.Max(4, ((Width - 2) * _value) / 100);
                    Rectangle fill = new Rectangle(1, 1, fillW, Height - 2);
                    using (var br = new LinearGradientBrush(fill, AccentCyan, AccentBlue, LinearGradientMode.Horizontal))
                    {
                        e.Graphics.FillRectangle(br, fill);
                    }
                }
            }
        }
    }
}
