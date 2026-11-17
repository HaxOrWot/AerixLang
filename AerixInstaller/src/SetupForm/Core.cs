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
        private AerixProgressBar _uninstProgress;
        private Label _lblUninstStatus;
        private Label _lblUninstNote;
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
        
    

