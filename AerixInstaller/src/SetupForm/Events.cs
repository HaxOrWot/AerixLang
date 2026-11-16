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


    }
}
