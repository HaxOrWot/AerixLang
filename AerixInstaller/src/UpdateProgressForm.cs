using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;

namespace AerixSetup
{
    public sealed class UpdateProgressForm : Form
    {
        private static readonly Color BgWindow = Color.FromArgb(14, 22, 38);        // #0E1626
        private static readonly Color BgHeader = Color.FromArgb(7, 11, 20);         // #070B14
        private static readonly Color BgCard = Color.FromArgb(20, 31, 54);          // #141F36
        private static readonly Color BgInput = Color.FromArgb(10, 16, 28);         // #0A101C
        private static readonly Color BorderSubtle = Color.FromArgb(34, 50, 80);    // #223250
        private static readonly Color TextPrimary = Color.FromArgb(241, 245, 249);
        private static readonly Color TextMuted = Color.FromArgb(148, 163, 184);
        private static readonly Color AccentCyan = Color.FromArgb(0, 229, 255);     // Electric Cyan
        private static readonly Color AccentBlue = Color.FromArgb(59, 130, 246);    // Electric Blue
        private static readonly Color AccentGreen = Color.FromArgb(16, 185, 129);   // Emerald
        private static readonly Color AccentDanger = Color.FromArgb(239, 68, 68);   // Crimson

        private readonly StableReleaseInfo _rel;
        private readonly string _installDir;
        private readonly bool _skipIde;

        private Label _lblTitle;
        private Label _lblSubtitle;
        private Label _lblStatus;
        private SimpleProgressBar _progressBar;
        private Button _btnClose;
        private bool _dragActive = false;
        private Point _dragOffset;

        public bool Success { get; private set; }

        public UpdateProgressForm(StableReleaseInfo rel, string installDir, bool skipIde)
        {
            _rel = rel;
            _installDir = installDir;
            _skipIde = skipIde;

            InitializeUi();
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

        private void InitializeUi()
        {
            Text = "Aerix Toolchain Updater";
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            Size = new Size(540, 240);
            BackColor = BgWindow;
            ForeColor = TextPrimary;

            try
            {
                string selfExe = Assembly.GetExecutingAssembly().Location;
                if (!string.IsNullOrEmpty(selfExe) && File.Exists(selfExe))
                {
                    Icon = Icon.ExtractAssociatedIcon(selfExe);
                }
            }
            catch { }

            // Custom draggable Title Bar
            Panel titleBar = new Panel
            {
                Dock = DockStyle.Top,
                Height = 36,
                BackColor = BgHeader
            };
            titleBar.MouseDown += OnTitleMouseDown;
            titleBar.MouseMove += OnTitleMouseMove;
            titleBar.MouseUp += OnTitleMouseUp;

            Label titleLabel = new Label
            {
                Text = "Aerix Toolchain Updater",
                ForeColor = TextMuted,
                Font = new Font("Segoe UI Semibold", 9F, FontStyle.Regular),
                Location = new Point(14, 9),
                AutoSize = true
            };
            titleLabel.MouseDown += OnTitleMouseDown;
            titleLabel.MouseMove += OnTitleMouseMove;
            titleLabel.MouseUp += OnTitleMouseUp;
            titleBar.Controls.Add(titleLabel);

            // Top Cyan Accent line
            Panel accentLine = new Panel
            {
                Dock = DockStyle.Top,
                Height = 2
            };
            accentLine.Paint += delegate(object s, PaintEventArgs e)
            {
                var r = new Rectangle(0, 0, accentLine.Width, accentLine.Height);
                using (var br = new LinearGradientBrush(r, AccentCyan, AccentBlue, LinearGradientMode.Horizontal))
                {
                    e.Graphics.FillRectangle(br, r);
                }
            };

            // Main Content Panel
            Panel content = new Panel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(26, 18, 26, 18)
            };

            _lblTitle = new Label
            {
                Text = "Updating Aerix to v" + (_rel != null ? _rel.Version : ""),
                Font = new Font("Segoe UI", 13F, FontStyle.Bold),
                ForeColor = AccentCyan,
                Location = new Point(26, 18),
                AutoSize = true
            };

            _lblSubtitle = new Label
            {
                Text = "Downloading and applying the latest verified stable release...",
                Font = new Font("Segoe UI", 9.2F, FontStyle.Regular),
                ForeColor = TextMuted,
                Location = new Point(26, 48),
                AutoSize = true
            };

            _progressBar = new SimpleProgressBar
            {
                Location = new Point(26, 84),
                Size = new Size(488, 16),
                Value = 10
            };

            _lblStatus = new Label
            {
                Text = "Connecting to GitHub...",
                Font = new Font("Segoe UI", 8.6F, FontStyle.Regular),
                ForeColor = TextMuted,
                Location = new Point(26, 112),
                Size = new Size(488, 20),
                AutoEllipsis = true
            };

            _btnClose = new Button
            {
                Text = "Updating...",
                Size = new Size(114, 34),
                Location = new Point(400, 144),
                FlatStyle = FlatStyle.Flat,
                BackColor = BgCard,
                ForeColor = TextMuted,
                Font = new Font("Segoe UI Semibold", 9.2F),
                Enabled = false,
                Cursor = Cursors.Hand
            };
            _btnClose.FlatAppearance.BorderSize = 1;
            _btnClose.FlatAppearance.BorderColor = BorderSubtle;
            _btnClose.Click += delegate { Close(); };

            content.Controls.Add(_lblTitle);
            content.Controls.Add(_lblSubtitle);
            content.Controls.Add(_progressBar);
            content.Controls.Add(_lblStatus);
            content.Controls.Add(_btnClose);

            Controls.Add(content);
            Controls.Add(titleBar);
            Controls.Add(accentLine);

            Paint += delegate(object s, PaintEventArgs e)
            {
                using (var pen = new Pen(BorderSubtle, 1))
                {
                    e.Graphics.DrawRectangle(pen, 0, 0, Width - 1, Height - 1);
                }
            };

            Shown += OnShown;
        }

        private void OnShown(object sender, EventArgs e)
        {
            var t = new Thread(RunUpdateWorker);
            t.IsBackground = true;
            t.Start();
        }

        private void RunUpdateWorker()
        {
            UpdateResult res = InstallerEngine.RunAutoUpdate(
                false,
                false,
                _skipIde,
                _installDir,
                delegate(int pct, string status, string logLine)
                {
                    try
                    {
                        if (!IsDisposed && IsHandleCreated)
                        {
                            BeginInvoke((MethodInvoker)delegate
                            {
                                _progressBar.Value = Math.Max(0, Math.Min(100, pct));
                                if (!string.IsNullOrEmpty(status))
                                {
                                    _lblStatus.Text = status;
                                }
                            });
                        }
                    }
                    catch { }
                });

            Success = res.Success;

            try
            {
                if (!IsDisposed && IsHandleCreated)
                {
                    BeginInvoke((MethodInvoker)delegate
                    {
                        if (res.Success)
                        {
                            _lblTitle.Text = "Update Complete!";
                            _lblTitle.ForeColor = AccentGreen;
                            _lblSubtitle.Text = "Aerix was successfully updated to v" + res.LatestVersion + "!";
                            _lblStatus.Text = "All binaries, standard library, and IDE tooling are ready.";
                            _progressBar.Value = 100;
                            _btnClose.Text = "Finish";
                            _btnClose.BackColor = AccentCyan;
                            _btnClose.ForeColor = Color.FromArgb(7, 11, 20);
                            _btnClose.FlatAppearance.BorderSize = 0;
                            _btnClose.Enabled = true;
                        }
                        else
                        {
                            _lblTitle.Text = "Update Failed";
                            _lblTitle.ForeColor = AccentDanger;
                            _lblSubtitle.Text = res.Message;
                            _lblStatus.Text = "See " + (string.IsNullOrEmpty(res.LogPath) ? "updater.log" : res.LogPath) + " for details.";
                            _btnClose.Text = "Close";
                            _btnClose.BackColor = AccentDanger;
                            _btnClose.ForeColor = Color.White;
                            _btnClose.FlatAppearance.BorderSize = 0;
                            _btnClose.Enabled = true;
                        }
                    });
                }
            }
            catch { }
        }

        private void OnTitleMouseDown(object sender, MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                _dragActive = true;
                _dragOffset = e.Location;
            }
        }

        private void OnTitleMouseMove(object sender, MouseEventArgs e)
        {
            if (_dragActive)
            {
                Point screen = PointToScreen(e.Location);
                Location = new Point(screen.X - _dragOffset.X, screen.Y - _dragOffset.Y);
            }
        }

        private void OnTitleMouseUp(object sender, MouseEventArgs e)
        {
            _dragActive = false;
        }

        private sealed class SimpleProgressBar : Control
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

            public SimpleProgressBar()
            {
                SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint, true);
            }

            protected override void OnPaint(PaintEventArgs e)
            {
                Graphics g = e.Graphics;
                g.SmoothingMode = SmoothingMode.AntiAlias;

                Rectangle track = new Rectangle(0, 0, Width - 1, Height - 1);
                using (var brush = new SolidBrush(BgInput))
                using (var pen = new Pen(BorderSubtle, 1))
                {
                    FillRoundedRect(g, brush, track, 5);
                    DrawRoundedRect(g, pen, track, 5);
                }

                if (_value > 0)
                {
                    int fillWidth = Math.Max(6, (int)((ClientRectangle.Width * _value) / 100.0));
                    var fillRect = new Rectangle(1, 1, fillWidth, ClientRectangle.Height - 2);
                    using (var fillBrush = new LinearGradientBrush(fillRect, AccentCyan, AccentBlue, LinearGradientMode.Horizontal))
                    {
                        FillRoundedRect(g, fillBrush, fillRect, 4);
                    }
                }
            }
        }
    }
}
