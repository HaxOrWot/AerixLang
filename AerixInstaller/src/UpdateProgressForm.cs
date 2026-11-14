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
        private static readonly Color BgWindow = Color.FromArgb(18, 27, 46);      // #121B2E
        private static readonly Color BgHeader = Color.FromArgb(11, 16, 28);      // #0B101C
        private static readonly Color BgCard = Color.FromArgb(23, 34, 59);        // #17223B
        private static readonly Color BorderSubtle = Color.FromArgb(36, 52, 82);  // #243452
        private static readonly Color TextPrimary = Color.FromArgb(235, 242, 252);
        private static readonly Color TextMuted = Color.FromArgb(142, 160, 189);
        private static readonly Color AccentCyan = Color.FromArgb(0, 220, 255);   // #00DCFF
        private static readonly Color AccentGreen = Color.FromArgb(34, 211, 153);
        private static readonly Color AccentDanger = Color.FromArgb(244, 91, 105);

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

        private void InitializeUi()
        {
            Text = "Aerix Toolchain Updater";
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.CenterScreen;
            Size = new Size(520, 230);
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
                Font = new Font("Segoe UI", 9F, FontStyle.Regular),
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
                Height = 2,
                BackColor = AccentCyan
            };

            // Main Content Panel
            Panel content = new Panel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(24, 16, 24, 16)
            };

            _lblTitle = new Label
            {
                Text = "Updating Aerix to v" + (_rel != null ? _rel.Version : ""),
                Font = new Font("Segoe UI", 12F, FontStyle.Bold),
                ForeColor = AccentCyan,
                Location = new Point(24, 16),
                AutoSize = true
            };

            _lblSubtitle = new Label
            {
                Text = "Downloading and applying the latest stable toolchain...",
                Font = new Font("Segoe UI", 9F, FontStyle.Regular),
                ForeColor = TextMuted,
                Location = new Point(24, 46),
                AutoSize = true
            };

            _progressBar = new SimpleProgressBar
            {
                Location = new Point(24, 80),
                Size = new Size(472, 16),
                Value = 10
            };

            _lblStatus = new Label
            {
                Text = "Connecting to GitHub...",
                Font = new Font("Segoe UI", 8.5F, FontStyle.Regular),
                ForeColor = TextMuted,
                Location = new Point(24, 108),
                Size = new Size(472, 20),
                AutoEllipsis = true
            };

            _btnClose = new Button
            {
                Text = "Updating...",
                Size = new Size(110, 32),
                Location = new Point(386, 140),
                FlatStyle = FlatStyle.Flat,
                BackColor = BgCard,
                ForeColor = TextMuted,
                Font = new Font("Segoe UI", 9F, FontStyle.Bold),
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
                            _lblStatus.Text = "All binaries, standard library, and editor tooling are up to date.";
                            _progressBar.Value = 100;
                            _btnClose.Text = "Finish";
                            _btnClose.BackColor = AccentCyan;
                            _btnClose.ForeColor = Color.FromArgb(11, 16, 28);
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

                using (var brush = new SolidBrush(Color.FromArgb(10, 16, 28)))
                {
                    g.FillRectangle(brush, ClientRectangle);
                }

                if (_value > 0)
                {
                    int fillWidth = (int)((ClientRectangle.Width * _value) / 100.0);
                    var fillRect = new Rectangle(0, 0, fillWidth, ClientRectangle.Height);
                    using (var fillBrush = new SolidBrush(AccentCyan))
                    {
                        g.FillRectangle(fillBrush, fillRect);
                    }
                }

                using (var pen = new Pen(BorderSubtle, 1))
                {
                    g.DrawRectangle(pen, 0, 0, Width - 1, Height - 1);
                }
            }
        }
    }
}
