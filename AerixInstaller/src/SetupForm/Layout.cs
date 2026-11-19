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
            Controls.Add(_sidebar);
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
            string[] steps = _uninstallMode
                ? new string[] { "Confirm Removal", "Uninstalling", "Complete" }
                : new string[] { "Welcome & License", "Options & IDEs", "Installing", "Ready to Code" };
            int y = 106;
            for (int i = 0; i < steps.Length; i++)
            {
                bool active = (i == _pageIndex);
                bool done = (i < _pageIndex) || (i == _pageIndex && _uninstallMode && _uninstDone);

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


    }
}
