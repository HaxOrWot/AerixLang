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
        // Modernized Theme Palette (Deep Obsidian Navy + Aerix Electric Cyan & Emerald)
        private static readonly Color BgWindow = Color.FromArgb(14, 22, 38);        // #0E1626
        private static readonly Color BgSidebar = Color.FromArgb(9, 15, 27);        // #090F1B
        private static readonly Color BgHeader = Color.FromArgb(7, 11, 20);         // #070B14
        private static readonly Color BgCard = Color.FromArgb(20, 31, 54);          // #141F36
        private static readonly Color BgInput = Color.FromArgb(10, 16, 28);         // #0A101C
        private static readonly Color BorderSubtle = Color.FromArgb(34, 50, 80);    // #223250
        private static readonly Color BorderHighlight = Color.FromArgb(0, 180, 216);
        private static readonly Color TextPrimary = Color.FromArgb(241, 245, 249);  // Slate 100
        private static readonly Color TextMuted = Color.FromArgb(148, 163, 184);    // Slate 400
        private static readonly Color AccentCyan = Color.FromArgb(0, 229, 255);     // Electric Cyan #00E5FF
        private static readonly Color AccentBlue = Color.FromArgb(59, 130, 246);    // Electric Blue #3B82F6
        private static readonly Color AccentGreen = Color.FromArgb(16, 185, 129);   // Emerald #10B981
        private static readonly Color AccentDanger = Color.FromArgb(239, 68, 68);   // Crimson #EF4444

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
            ClientSize = new Size(800, 520);
            BackColor = BgWindow;
            ForeColor = TextPrimary;
            Font = new Font("Segoe UI", 9.5F, FontStyle.Regular);
            Text = "Aerix " + _version + " Setup Wizard";

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

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            // Draw subtle outer border around borderless form
            using (var p = new Pen(BorderSubtle, 1))
            {
                e.Graphics.DrawRectangle(p, 0, 0, Width - 1, Height - 1);
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
            catch { }

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
            catch { }
        }

        private void BuildChrome()
        {
            // Top accent gradient line (2px cyan-to-blue)
            var topAccent = new Panel();
            topAccent.Dock = DockStyle.Top;
            topAccent.Height = 2;
            topAccent.Paint += delegate(object s, PaintEventArgs e)
            {
                var r = new Rectangle(0, 0, topAccent.Width, topAccent.Height);
                using (var br = new LinearGradientBrush(r, AccentCyan, AccentBlue, LinearGradientMode.Horizontal))
                {
                    e.Graphics.FillRectangle(br, r);
                }
            };

            // Custom Title Bar (38px)
            var titleBar = new Panel();
            titleBar.Dock = DockStyle.Top;
            titleBar.Height = 38;
            titleBar.BackColor = BgHeader;
            titleBar.MouseDown += OnHeaderMouseDown;
            titleBar.MouseMove += OnHeaderMouseMove;
            titleBar.MouseUp += OnHeaderMouseUp;

            var lblTitle = new Label();
            lblTitle.Text = _uninstallMode
                ? "Aerix " + _version + "  —  Uninstallation Wizard"
                : "Aerix " + _version + "  —  Windows Setup Wizard";
            lblTitle.ForeColor = TextMuted;
            lblTitle.Font = new Font("Segoe UI Semibold", 9.2F);
            lblTitle.UseMnemonic = false;
            lblTitle.AutoSize = false;
            lblTitle.Size = new Size(540, 38);
            lblTitle.Location = new Point(16, 0);
            lblTitle.TextAlign = ContentAlignment.MiddleLeft;
            lblTitle.MouseDown += OnHeaderMouseDown;
            lblTitle.MouseMove += OnHeaderMouseMove;
            lblTitle.MouseUp += OnHeaderMouseUp;

            var btnClose = CreateTitleButton("×", new Point(titleBar.Width - 44, 0), true);
            btnClose.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            btnClose.Click += delegate
            {
                if (!_isBusy) Close();
            };

            var btnMin = CreateTitleButton("—", new Point(titleBar.Width - 88, 0), false);
            btnMin.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            btnMin.Click += delegate
            {
                WindowState = FormWindowState.Minimized;
            };

            titleBar.Controls.Add(lblTitle);
            titleBar.Controls.Add(btnMin);
            titleBar.Controls.Add(btnClose);

            // Left Sidebar (224px)
            _sidebar = new Panel();
            _sidebar.Dock = DockStyle.Left;
            _sidebar.Width = 224;
            _sidebar.BackColor = BgSidebar;
            _sidebar.Paint += PaintSidebar;

            // Footer Bar (58px)
            _footer = new Panel();
            _footer.Dock = DockStyle.Bottom;
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
            _contentHost.Padding = new Padding(24, 18, 24, 16);

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
            b.FlatAppearance.MouseOverBackColor = isClose ? Color.FromArgb(220, 38, 38) : Color.FromArgb(30, 44, 72);
            b.BackColor = BgHeader;
            b.ForeColor = TextMuted;
            b.Font = new Font("Segoe UI", 10.5F);
            b.Size = new Size(44, 38);
            b.Location = loc;
            b.Cursor = Cursors.Hand;
            b.TabStop = false;
            b.MouseEnter += delegate { b.ForeColor = Color.White; };
            b.MouseLeave += delegate { b.ForeColor = TextMuted; };
            return b;
        }

        private static GraphicsPath CreateRoundedPath(Rectangle rect, int radius)
        {
            var path = new GraphicsPath();
            if (radius <= 0)
            {
                path.AddRectangle(rect);
                return path;
            }
            int d = radius * 2;
            path.AddArc(rect.X, rect.Y, d, d, 180, 90);
            path.AddArc(rect.Right - d, rect.Y, d, d, 270, 90);
            path.AddArc(rect.Right - d, rect.Bottom - d, d, d, 0, 90);
            path.AddArc(rect.X, rect.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }

        private static void FillRoundedRect(Graphics g, Brush brush, Rectangle rect, int radius)
        {
            using (GraphicsPath p = CreateRoundedPath(rect, radius))
            {
                g.FillPath(brush, p);
            }
        }

        private static void DrawRoundedRect(Graphics g, Pen pen, Rectangle rect, int radius)
        {
            using (GraphicsPath p = CreateRoundedPath(rect, radius))
            {
                g.DrawPath(pen, p);
            }
        }

        private void PaintSidebar(object sender, PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;

            // Right vertical divider line
            using (var pen = new Pen(BorderSubtle, 1))
            {
                g.DrawLine(pen, _sidebar.Width - 1, 0, _sidebar.Width - 1, _sidebar.Height);
            }

            // Brand Header with Icon & Version Badge
            if (_brandImg != null)
            {
                g.DrawImage(_brandImg, new Rectangle(20, 20, 36, 36));
            }
            using (var fBrand = new Font("Segoe UI", 13.5F, FontStyle.Bold))
            using (var bTitle = new SolidBrush(TextPrimary))
            {
                g.DrawString("AERIX", fBrand, bTitle, new PointF(62, 17));
            }

            // Version Pill Badge
            Rectangle verBadge = new Rectangle(62, 41, 102, 18);
            using (var brBadge = new SolidBrush(Color.FromArgb(16, 42, 68)))
            using (var penBadge = new Pen(Color.FromArgb(0, 160, 200), 1))
            using (var fVer = new Font("Segoe UI Semibold", 8F))
            using (var bCyan = new SolidBrush(AccentCyan))
            {
                FillRoundedRect(g, brBadge, verBadge, 4);
                DrawRoundedRect(g, penBadge, verBadge, 4);
                var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center };
                g.DrawString("v" + _version, fVer, bCyan, verBadge, sf);
            }

            // Step Indicator Navigation
            string[] steps = { "Welcome & License", "Options & IDEs", "Installing", "Ready to Code" };
            int y = 106;
            for (int i = 0; i < steps.Length; i++)
            {
                bool active = (i == _pageIndex);
                bool done = (i < _pageIndex);

                // Connecting vertical step lines
                if (i < steps.Length - 1)
                {
                    Color lineCol = done ? AccentGreen : BorderSubtle;
                    using (var penLine = new Pen(lineCol, 2))
                    {
                        g.DrawLine(penLine, 32, y + 24, 32, y + 50);
                    }
                }

                // Step Circle
                Rectangle circle = new Rectangle(21, y, 22, 22);
                Color fill = active ? AccentCyan : (done ? AccentGreen : Color.FromArgb(18, 28, 48));
                using (var brFill = new SolidBrush(fill))
                {
                    g.FillEllipse(brFill, circle);
                }

                if (active)
                {
                    // Outer glow halo around active circle
                    Rectangle halo = new Rectangle(circle.X - 3, circle.Y - 3, circle.Width + 6, circle.Height + 6);
                    using (var penHalo = new Pen(Color.FromArgb(60, 0, 229, 255), 2))
                    {
                        g.DrawEllipse(penHalo, halo);
                    }
                }
                else if (!done)
                {
                    using (var penC = new Pen(BorderSubtle, 1.5F))
                    {
                        g.DrawEllipse(penC, circle);
                    }
                }

                string badgeTxt = done ? "✓" : (i + 1).ToString();
                Color badgeFg = (active || done) ? BgHeader : TextMuted;
                using (var fNum = new Font("Segoe UI", 8.2F, FontStyle.Bold))
                using (var bNum = new SolidBrush(badgeFg))
                {
                    var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center };
                    g.DrawString(badgeTxt, fNum, bNum, new RectangleF(circle.X, circle.Y + 0.5F, circle.Width, circle.Height), sf);
                }

                using (var fStep = new Font("Segoe UI", 9.2F, active ? FontStyle.Bold : FontStyle.Regular))
                using (var bStep = new SolidBrush(active ? TextPrimary : (done ? AccentGreen : TextMuted)))
                {
                    g.DrawString(steps[i], fStep, bStep, new PointF(54, y + 2));
                }

                y += 52;
            }

            // Bottom Architecture Glass Card
            Rectangle archCard = new Rectangle(16, _sidebar.Height - 74, _sidebar.Width - 32, 54);
            using (var brCard = new SolidBrush(Color.FromArgb(14, 23, 40)))
            using (var penCard = new Pen(BorderSubtle, 1))
            {
                FillRoundedRect(g, brCard, archCard, 6);
                DrawRoundedRect(g, penCard, archCard, 6);
            }

            // Cyan indicator dot
            using (var brDot = new SolidBrush(AccentCyan))
            {
                g.FillEllipse(brDot, new Rectangle(28, archCard.Y + 14, 8, 8));
            }
            using (var fArch = new Font("Segoe UI Semibold", 8.4F))
            using (var bArch = new SolidBrush(TextPrimary))
            using (var fSub = new Font("Segoe UI", 7.8F))
            using (var bSub = new SolidBrush(TextMuted))
            {
                g.DrawString("Native x86-64 Backend", fArch, bArch, new PointF(42, archCard.Y + 10));
                g.DrawString("Zero External Dependencies", fSub, bSub, new PointF(42, archCard.Y + 28));
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

            var title = MakeHeaderLabel("Uninstall Aerix " + _version, 0, 6);
            _lblUninstInfo = new Label();
            _lblUninstInfo.Text = "This wizard will completely remove Aerix binaries, standard library, environment variables, PATH records, and .arx file associations from:\r\n\r\n" + _opts.InstallDir;
            _lblUninstInfo.ForeColor = TextPrimary;
            _lblUninstInfo.Font = new Font("Segoe UI", 9.6F);
            _lblUninstInfo.Location = new Point(0, 50);
            _lblUninstInfo.Size = new Size(740, 90);

            _lblUninstStatus = new Label();
            _lblUninstStatus.Text = "Click Uninstall to proceed.";
            _lblUninstStatus.ForeColor = TextMuted;
            _lblUninstStatus.Location = new Point(0, 160);
            _lblUninstStatus.Size = new Size(740, 24);

            _uninstProgress = new AerixProgressBar();
            _uninstProgress.Location = new Point(0, 192);
            _uninstProgress.Size = new Size(740, 16);

            _contentHost.Controls.Add(title);
            _contentHost.Controls.Add(_lblUninstInfo);
            _contentHost.Controls.Add(_lblUninstStatus);
            _contentHost.Controls.Add(_uninstProgress);

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
                        string eds = rep.InstalledEditors.Count > 0 ? string.Join(", ", rep.InstalledEditors.ToArray()) : "None detected (VSIX ready in editors\\)";
                        string smoke = string.IsNullOrEmpty(rep.SmokeTestSummary) ? "Skipped" : rep.SmokeTestSummary;
                        _lblFinishHeadline.Text = "Aerix " + rep.InstalledVersion + " Installed Successfully!";
                        _lblFinishHeadline.ForeColor = AccentGreen;
                        _lblFinishBody.Text = string.Format(
                            "Destination Folder:\r\n  {0}\r\n\r\n" +
                            "Core Toolchain:\r\n  arx.exe, arxc.exe, Updater.exe (Native PE32+)\r\n\r\n" +
                            "IDE Integrations:\r\n  {1}\r\n\r\n" +
                            "Verification:\r\n  {2}",
                            _opts.InstallDir, eds, smoke);
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
            l.Font = new Font("Segoe UI", 15.5F, FontStyle.Bold);
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
                var r = new Rectangle(0, 0, c.Width - 1, c.Height - 1);
                using (var br = new SolidBrush(BgCard))
                using (var pen = new Pen(BorderSubtle, 1))
                {
                    FillRoundedRect(e.Graphics, br, r, 7);
                    DrawRoundedRect(e.Graphics, pen, r, 7);
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
            b.Size = new Size(96, 34);
            b.FlatStyle = FlatStyle.Flat;
            b.Cursor = Cursors.Hand;
            b.Font = new Font("Segoe UI Semibold", 9.2F);
            if (primary)
            {
                b.BackColor = AccentCyan;
                b.ForeColor = BgHeader;
                b.FlatAppearance.BorderSize = 0;
                b.FlatAppearance.MouseOverBackColor = Color.FromArgb(56, 238, 255);
            }
            else
            {
                b.BackColor = BgCard;
                b.ForeColor = TextPrimary;
                b.FlatAppearance.BorderSize = 1;
                b.FlatAppearance.BorderColor = BorderSubtle;
                b.FlatAppearance.MouseOverBackColor = Color.FromArgb(28, 44, 76);
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
                    FillRoundedRect(e.Graphics, bg, track, 5);
                    DrawRoundedRect(e.Graphics, pen, track, 5);
                }
                if (_value > 0)
                {
                    int fillW = Math.Max(6, ((Width - 2) * _value) / 100);
                    Rectangle fill = new Rectangle(1, 1, fillW, Height - 2);
                    using (var br = new LinearGradientBrush(fill, AccentCyan, AccentBlue, LinearGradientMode.Horizontal))
                    {
                        FillRoundedRect(e.Graphics, br, fill, 4);
                    }
                }
            }
        }
    }
}
