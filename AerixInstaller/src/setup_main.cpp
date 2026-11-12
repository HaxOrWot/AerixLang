#include "installer_engine.hpp"
#include "resource.h"

#include <windows.h>
#include <commctrl.h>
#include <shellapi.h>
#include <shlobj.h>

#include <algorithm>
#include <atomic>
#include <cwctype>
#include <filesystem>
#include <string>
#include <thread>
#include <vector>

namespace fs = std::filesystem;

namespace {

constexpr int kClientW = 560;
constexpr int kClientH = 410;
constexpr int kHeaderH = 62;
constexpr int kFooterH = 48;

enum WizardPage {
    PAGE_WELCOME = 0,
    PAGE_LICENSE = 1,
    PAGE_DIR     = 2,
    PAGE_OPTIONS = 3,
    PAGE_INSTALL = 4,
    PAGE_FINISH  = 5
};

struct CliArgs {
    bool silent = false;
    bool uninstall = false;
    bool no_path = false;
    bool no_assoc = false;
    bool no_vscode = false;
    bool no_antigravity = false;
    std::wstring dir_override;
};

struct AppState {
    HINSTANCE hinst = nullptr;
    HWND hwnd = nullptr;
    HFONT font_ui = nullptr;
    HFONT font_bold = nullptr;
    HFONT font_title = nullptr;
    HFONT font_mono = nullptr;
    HBITMAP bmp_side = nullptr;
    HBITMAP bmp_banner = nullptr;
    HBRUSH white_brush = nullptr;

    int current_page = PAGE_WELCOME;
    std::vector<HWND> page_ctrls[6];

    HWND btn_back = nullptr;
    HWND btn_next = nullptr;
    HWND btn_cancel = nullptr;

    HWND header_title = nullptr;
    HWND header_sub = nullptr;
    HWND banner_pic = nullptr;
    HWND side_pic = nullptr;

    HWND edit_license = nullptr;
    HWND chk_accept = nullptr;
    HWND edit_dir = nullptr;
    HWND btn_browse = nullptr;

    HWND chk_env = nullptr;
    HWND chk_assoc = nullptr;
    HWND chk_vscode = nullptr;
    HWND chk_antigravity = nullptr;

    HWND progress_bar = nullptr;
    HWND lbl_status = nullptr;
    HWND edit_log = nullptr;

    HWND chk_open_term = nullptr;
    HWND chk_open_guide = nullptr;
    HWND lbl_finish_body = nullptr;

    std::atomic<bool> installing{false};
    bool install_succeeded = false;
    std::wstring installed_dir;
    std::wstring last_error;
};

AppState g_app;

std::wstring ToLowerW(std::wstring s) {
    for (wchar_t& c : s) c = static_cast<wchar_t>(towlower(c));
    return s;
}

CliArgs ParseCommandLine() {
    CliArgs args;
    wchar_t exe_buf[MAX_PATH] = {};
    if (GetModuleFileNameW(nullptr, exe_buf, MAX_PATH) > 0) {
        std::wstring base = ToLowerW(fs::path(exe_buf).filename().wstring());
        if (base.find(L"uninstall") != std::wstring::npos) {
            args.uninstall = true;
        }
    }

    int argc = 0;
    LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv) return args;

    for (int i = 1; i < argc; ++i) {
        std::wstring raw = argv[i];
        std::wstring low = ToLowerW(raw);
        if (low == L"--silent" || low == L"/silent" || low == L"/verysilent") {
            args.silent = true;
        } else if (low == L"--uninstall" || low == L"/uninstall") {
            args.uninstall = true;
        } else if (low == L"--no-path") {
            args.no_path = true;
        } else if (low == L"--no-assoc") {
            args.no_assoc = true;
        } else if (low == L"--no-vscode") {
            args.no_vscode = true;
        } else if (low == L"--no-antigravity") {
            args.no_antigravity = true;
        } else if (low.rfind(L"--dir=", 0) == 0) {
            args.dir_override = raw.substr(6);
        } else if (low.rfind(L"/dir=", 0) == 0) {
            args.dir_override = raw.substr(5);
        } else if (low == L"--dir" && i + 1 < argc) {
            args.dir_override = argv[++i];
        }
    }
    LocalFree(argv);
    return args;
}

std::wstring GetControlText(HWND h) {
    int len = GetWindowTextLengthW(h);
    std::wstring s(static_cast<size_t>(len + 1), L'\0');
    GetWindowTextW(h, s.data(), len + 1);
    if (!s.empty() && s.back() == L'\0') s.pop_back();
    return s;
}

void AppendLogLine(const std::wstring& line) {
    if (!g_app.edit_log) return;
    int len = GetWindowTextLengthW(g_app.edit_log);
    SendMessageW(g_app.edit_log, EM_SETSEL, len, len);
    std::wstring text = line + L"\r\n";
    SendMessageW(g_app.edit_log, EM_REPLACESEL, FALSE, reinterpret_cast<LPARAM>(text.c_str()));
}

int CALLBACK BrowseCallbackProc(HWND hwnd, UINT uMsg, LPARAM, LPARAM lpData) {
    if (uMsg == BFFM_INITIALIZED && lpData != 0) {
        SendMessageW(hwnd, BFFM_SETSELECTIONW, TRUE, lpData);
    }
    return 0;
}

void BrowseForDestination() {
    std::wstring current = GetControlText(g_app.edit_dir);
    BROWSEINFOW bi{};
    bi.hwndOwner = g_app.hwnd;
    bi.lpszTitle = L"Select the destination folder for Aerix:";
    bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE | BIF_EDITBOX;
    bi.lpfn = BrowseCallbackProc;
    bi.lParam = reinterpret_cast<LPARAM>(current.c_str());

    PIDLIST_ABSOLUTE pidl = SHBrowseForFolderW(&bi);
    if (pidl) {
        wchar_t path[MAX_PATH] = {};
        if (SHGetPathFromIDListW(pidl, path)) {
            fs::path chosen(path);
            std::wstring leaf = ToLowerW(chosen.filename().wstring());
            if (leaf != L"aerix") {
                chosen /= L"Aerix";
            }
            SetWindowTextW(g_app.edit_dir, chosen.wstring().c_str());
        }
        CoTaskMemFree(pidl);
    }
}

void UpdatePageChrome(int page) {
    const wchar_t* titles[] = {
        L"",
        L"License Agreement",
        L"Select Destination Location",
        L"Select Additional Tasks",
        L"Installing Aerix",
        L""
    };
    const wchar_t* subs[] = {
        L"",
        L"Please read the following important information before continuing.",
        L"Where should Aerix Native Systems Language be installed?",
        L"Which additional tasks should be performed?",
        L"Please wait while Setup installs Aerix on your computer.",
        L""
    };

    bool show_banner = (page >= PAGE_LICENSE && page <= PAGE_INSTALL);
    ShowWindow(g_app.header_title, show_banner ? SW_SHOW : SW_HIDE);
    ShowWindow(g_app.header_sub, show_banner ? SW_SHOW : SW_HIDE);
    ShowWindow(g_app.banner_pic, show_banner ? SW_SHOW : SW_HIDE);
    if (show_banner) {
        SetWindowTextW(g_app.header_title, titles[page]);
        SetWindowTextW(g_app.header_sub, subs[page]);
    }

    EnableWindow(g_app.btn_back, page > PAGE_WELCOME && page < PAGE_INSTALL);
    EnableWindow(g_app.btn_cancel, page != PAGE_INSTALL && page != PAGE_FINISH);
    ShowWindow(g_app.btn_back, page == PAGE_FINISH ? SW_HIDE : SW_SHOW);
    ShowWindow(g_app.btn_cancel, page == PAGE_FINISH ? SW_HIDE : SW_SHOW);

    if (page == PAGE_LICENSE) {
        bool accepted = SendMessageW(g_app.chk_accept, BM_GETCHECK, 0, 0) == BST_CHECKED;
        EnableWindow(g_app.btn_next, accepted);
        SetWindowTextW(g_app.btn_next, L"&Next >");
    } else if (page == PAGE_OPTIONS) {
        EnableWindow(g_app.btn_next, TRUE);
        SetWindowTextW(g_app.btn_next, L"&Install");
    } else if (page == PAGE_INSTALL) {
        EnableWindow(g_app.btn_next, FALSE);
        SetWindowTextW(g_app.btn_next, L"&Install");
    } else if (page == PAGE_FINISH) {
        EnableWindow(g_app.btn_next, TRUE);
        SetWindowTextW(g_app.btn_next, L"&Finish");
    } else {
        EnableWindow(g_app.btn_next, TRUE);
        SetWindowTextW(g_app.btn_next, L"&Next >");
    }
}

void ShowPage(int page) {
    g_app.current_page = page;
    for (int p = 0; p < 6; ++p) {
        int cmd = (p == page) ? SW_SHOW : SW_HIDE;
        for (HWND h : g_app.page_ctrls[p]) {
            ShowWindow(h, cmd);
        }
    }
    UpdatePageChrome(page);
    InvalidateRect(g_app.hwnd, nullptr, TRUE);
}

void StartInstallWorker() {
    InstallOptions opts;
    opts.install_dir = GetControlText(g_app.edit_dir);
    opts.configure_env = SendMessageW(g_app.chk_env, BM_GETCHECK, 0, 0) == BST_CHECKED;
    opts.file_associations = SendMessageW(g_app.chk_assoc, BM_GETCHECK, 0, 0) == BST_CHECKED;
    opts.install_vscode = SendMessageW(g_app.chk_vscode, BM_GETCHECK, 0, 0) == BST_CHECKED;
    opts.install_antigravity = SendMessageW(g_app.chk_antigravity, BM_GETCHECK, 0, 0) == BST_CHECKED;

    g_app.installed_dir = opts.install_dir;
    g_app.installing = true;
    ShowPage(PAGE_INSTALL);

    std::thread([opts]() {
        std::wstring err;
        bool ok = RunInstall(
            g_app.hinst,
            opts,
            [](int pct, const std::wstring& msg) {
                PostMessageW(g_app.hwnd, WM_INSTALL_PROGRESS, static_cast<WPARAM>(pct), 0);
                auto* copy = new std::wstring(msg);
                PostMessageW(g_app.hwnd, WM_INSTALL_LOG, 0, reinterpret_cast<LPARAM>(copy));
            },
            err);
        g_app.install_succeeded = ok;
        g_app.last_error = err;
        g_app.installing = false;
        PostMessageW(g_app.hwnd, WM_INSTALL_DONE, ok ? 1 : 0, 0);
    }).detach();
}

HWND AddCtrl(int page, const wchar_t* cls, const wchar_t* text, DWORD style,
             int x, int y, int w, int h, int id = 0, HFONT font = nullptr) {
    HWND ctrl = CreateWindowExW(
        0, cls, text, WS_CHILD | style,
        x, y, w, h, g_app.hwnd,
        reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)), g_app.hinst, nullptr);
    SendMessageW(ctrl, WM_SETFONT, reinterpret_cast<WPARAM>(font ? font : g_app.font_ui), TRUE);
    if (page >= 0 && page < 6) {
        g_app.page_ctrls[page].push_back(ctrl);
    }
    return ctrl;
}

void BuildWizardControls() {
    g_app.white_brush = CreateSolidBrush(RGB(255, 255, 255));
    g_app.font_ui = CreateFontW(-13, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                                DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_SWISS, L"Segoe UI");
    g_app.font_bold = CreateFontW(-13, 0, 0, 0, FW_SEMIBOLD, FALSE, FALSE, FALSE,
                                  DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                  CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_SWISS, L"Segoe UI");
    g_app.font_title = CreateFontW(-20, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
                                   DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                   CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_SWISS, L"Segoe UI");
    g_app.font_mono = CreateFontW(-12, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                                  DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                  CLEARTYPE_QUALITY, FIXED_PITCH | FF_MODERN, L"Consolas");

    g_app.bmp_side = static_cast<HBITMAP>(
        LoadImageW(g_app.hinst, MAKEINTRESOURCEW(IDB_WIZARD_SIDE), IMAGE_BITMAP, 168, kClientH - kFooterH, LR_DEFAULTCOLOR));
    g_app.bmp_banner = static_cast<HBITMAP>(
        LoadImageW(g_app.hinst, MAKEINTRESOURCEW(IDB_WIZARD_BAN), IMAGE_BITMAP, 56, 56, LR_DEFAULTCOLOR));

    // Shared header controls (pages 1..4)
    g_app.header_title = AddCtrl(-1, L"STATIC", L"", SS_LEFT, 18, 10, 450, 22, 0, g_app.font_bold);
    g_app.header_sub = AddCtrl(-1, L"STATIC", L"", SS_LEFT, 28, 33, 440, 20, 0, g_app.font_ui);
    g_app.banner_pic = AddCtrl(-1, L"STATIC", L"", SS_BITMAP | SS_CENTERIMAGE, kClientW - 64, 3, 56, 56, 0);
    if (g_app.bmp_banner) {
        SendMessageW(g_app.banner_pic, STM_SETIMAGE, IMAGE_BITMAP, reinterpret_cast<LPARAM>(g_app.bmp_banner));
    }

    // Shared footer buttons
    int btn_y = kClientH - 35;
    g_app.btn_back = AddCtrl(-1, L"BUTTON", L"< &Back", BS_PUSHBUTTON | WS_TABSTOP, 286, btn_y, 82, 25, IDC_BTN_BACK);
    g_app.btn_next = AddCtrl(-1, L"BUTTON", L"&Next >", BS_DEFPUSHBUTTON | WS_TABSTOP, 374, btn_y, 82, 25, IDC_BTN_NEXT);
    g_app.btn_cancel = AddCtrl(-1, L"BUTTON", L"Cancel", BS_PUSHBUTTON | WS_TABSTOP, 466, btn_y, 78, 25, IDC_BTN_CANCEL);

    // PAGE 0: Welcome
    g_app.side_pic = AddCtrl(PAGE_WELCOME, L"STATIC", L"", SS_BITMAP, 0, 0, 168, kClientH - kFooterH);
    if (g_app.bmp_side) {
        SendMessageW(g_app.side_pic, STM_SETIMAGE, IMAGE_BITMAP, reinterpret_cast<LPARAM>(g_app.bmp_side));
    }
    AddCtrl(PAGE_WELCOME, L"STATIC",
            L"Welcome to the Aerix Setup Wizard",
            SS_LEFT, 188, 24, 352, 52, 0, g_app.font_title);
    AddCtrl(PAGE_WELCOME, L"STATIC",
            L"This will install Aerix Native Systems Language v" AERIX_VERSION_WSTR L" on your computer.\r\n\r\n"
            L"Aerix now ships with the self-hosting native compiler (arx / arxc), standard runtime header (aerix_rt.h), "
            L"built-in modules, and official VS Code / Antigravity IDE support — requiring zero Python runtime.\r\n\r\n"
            L"Click Next to continue, or Cancel to exit Setup.",
            SS_LEFT, 188, 92, 352, 220, 0, g_app.font_ui);

    // PAGE 1: License
    AddCtrl(PAGE_LICENSE, L"STATIC",
            L"Please read the following License Agreement. You must accept the terms before continuing.",
            SS_LEFT, 22, kHeaderH + 14, 516, 20);
    g_app.edit_license = CreateWindowExW(
        WS_EX_CLIENTEDGE, L"EDIT", GetLicenseText(g_app.hinst).c_str(),
        WS_CHILD | WS_VSCROLL | ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL,
        22, kHeaderH + 40, 516, 205, g_app.hwnd,
        reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_EDIT_LICENSE)), g_app.hinst, nullptr);
    SendMessageW(g_app.edit_license, WM_SETFONT, reinterpret_cast<WPARAM>(g_app.font_mono), TRUE);
    g_app.page_ctrls[PAGE_LICENSE].push_back(g_app.edit_license);

    g_app.chk_accept = AddCtrl(PAGE_LICENSE, L"BUTTON",
                               L"I accept the terms in the License Agreement",
                               BS_AUTOCHECKBOX | WS_TABSTOP, 22, kHeaderH + 256, 360, 22, IDC_CHK_ACCEPT);

    // PAGE 2: Destination Directory
    AddCtrl(PAGE_DIR, L"STATIC",
            L"Setup will install Aerix into the following folder.\r\n\r\n"
            L"To continue, click Next. If you would like to select a different folder, click Browse.",
            SS_LEFT, 22, kHeaderH + 20, 516, 56);
    g_app.edit_dir = CreateWindowExW(
        WS_EX_CLIENTEDGE, L"EDIT", GetDefaultInstallDir().c_str(),
        WS_CHILD | ES_AUTOHSCROLL | WS_TABSTOP,
        22, kHeaderH + 92, 418, 24, g_app.hwnd,
        reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_EDIT_DIR)), g_app.hinst, nullptr);
    SendMessageW(g_app.edit_dir, WM_SETFONT, reinterpret_cast<WPARAM>(g_app.font_ui), TRUE);
    g_app.page_ctrls[PAGE_DIR].push_back(g_app.edit_dir);

    g_app.btn_browse = AddCtrl(PAGE_DIR, L"BUTTON", L"&Browse...", BS_PUSHBUTTON | WS_TABSTOP,
                               448, kHeaderH + 91, 90, 26, IDC_BTN_BROWSE);
    AddCtrl(PAGE_DIR, L"STATIC",
            L"Note: Installing under your user profile requires no Administrator (UAC) elevation.",
            SS_LEFT, 22, kHeaderH + 140, 516, 30);

    // PAGE 3: Options
    AddCtrl(PAGE_OPTIONS, L"STATIC",
            L"Select the additional tasks you would like Setup to perform while installing Aerix:",
            SS_LEFT, 22, kHeaderH + 18, 516, 22);
    g_app.chk_env = AddCtrl(PAGE_OPTIONS, L"BUTTON",
                            L"Add Aerix to User PATH and configure AERIX_* environment variables",
                            BS_AUTOCHECKBOX | WS_TABSTOP, 30, kHeaderH + 54, 500, 24, IDC_CHK_ENVPATH);
    SendMessageW(g_app.chk_env, BM_SETCHECK, BST_CHECKED, 0);

    g_app.chk_assoc = AddCtrl(PAGE_OPTIONS, L"BUTTON",
                              L"Associate .arx files with Aerix icons and Explorer Run/Build context menus",
                              BS_AUTOCHECKBOX | WS_TABSTOP, 30, kHeaderH + 88, 500, 24, IDC_CHK_FILEASSOC);
    SendMessageW(g_app.chk_assoc, BM_SETCHECK, BST_CHECKED, 0);

    g_app.chk_vscode = AddCtrl(PAGE_OPTIONS, L"BUTTON",
                               L"Install official extension (aerix-" AERIX_VERSION_WSTR L".vsix) in Visual Studio Code",
                               BS_AUTOCHECKBOX | WS_TABSTOP, 30, kHeaderH + 122, 500, 24, IDC_CHK_VSCODE);
    SendMessageW(g_app.chk_vscode, BM_SETCHECK, DetectVSCodeCli().empty() ? BST_UNCHECKED : BST_CHECKED, 0);

    g_app.chk_antigravity = AddCtrl(PAGE_OPTIONS, L"BUTTON",
                                    L"Install official extension (aerix-" AERIX_VERSION_WSTR L".vsix) in Antigravity IDE",
                                    BS_AUTOCHECKBOX | WS_TABSTOP, 30, kHeaderH + 156, 500, 24, IDC_CHK_ANTIGRAVITY);
    SendMessageW(g_app.chk_antigravity, BM_SETCHECK, DetectAntigravityCli().empty() ? BST_UNCHECKED : BST_CHECKED, 0);

    // PAGE 4: Installing
    g_app.lbl_status = AddCtrl(PAGE_INSTALL, L"STATIC", L"Preparing installation...", SS_LEFT,
                               22, kHeaderH + 16, 516, 20, IDC_STATIC_STATUS);
    g_app.progress_bar = AddCtrl(PAGE_INSTALL, PROGRESS_CLASSW, L"", PBS_SMOOTH,
                                 22, kHeaderH + 42, 516, 22, IDC_PROGRESS_BAR);
    SendMessageW(g_app.progress_bar, PBM_SETRANGE, 0, MAKELPARAM(0, 100));

    g_app.edit_log = CreateWindowExW(
        WS_EX_CLIENTEDGE, L"EDIT", L"",
        WS_CHILD | WS_VSCROLL | ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL,
        22, kHeaderH + 76, 516, 200, g_app.hwnd,
        reinterpret_cast<HMENU>(static_cast<INT_PTR>(IDC_EDIT_LOG)), g_app.hinst, nullptr);
    SendMessageW(g_app.edit_log, WM_SETFONT, reinterpret_cast<WPARAM>(g_app.font_mono), TRUE);
    g_app.page_ctrls[PAGE_INSTALL].push_back(g_app.edit_log);

    // PAGE 5: Finish
    HWND fin_side = AddCtrl(PAGE_FINISH, L"STATIC", L"", SS_BITMAP, 0, 0, 168, kClientH - kFooterH);
    if (g_app.bmp_side) {
        SendMessageW(fin_side, STM_SETIMAGE, IMAGE_BITMAP, reinterpret_cast<LPARAM>(g_app.bmp_side));
    }
    AddCtrl(PAGE_FINISH, L"STATIC",
            L"Completing the Aerix Setup Wizard",
            SS_LEFT, 188, 24, 352, 52, 0, g_app.font_title);
    g_app.lbl_finish_body = AddCtrl(
        PAGE_FINISH, L"STATIC",
        L"Aerix v" AERIX_VERSION_WSTR L" has been successfully installed on your computer.\r\n\r\n"
        L"Open a new terminal window and run 'arx --version' to get started. Restart open editors to load new PATH / extension updates.",
        SS_LEFT, 188, 92, 352, 110, 0, g_app.font_ui);
    g_app.chk_open_term = AddCtrl(PAGE_FINISH, L"BUTTON",
                                  L"Verify installation in Command Prompt (arx --version)",
                                  BS_AUTOCHECKBOX | WS_TABSTOP, 188, 214, 340, 22, IDC_CHK_OPEN_TERM);
    g_app.chk_open_guide = AddCtrl(PAGE_FINISH, L"BUTTON",
                                   L"Open GUIDE.md documentation",
                                   BS_AUTOCHECKBOX | WS_TABSTOP, 188, 244, 340, 22, IDC_CHK_OPEN_GUIDE);
}

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    switch (msg) {
        case WM_CREATE:
            g_app.hwnd = hwnd;
            BuildWizardControls();
            ShowPage(PAGE_WELCOME);
            return 0;

        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hwnd, &ps);
            RECT rc;
            GetClientRect(hwnd, &rc);

            if (g_app.current_page == PAGE_WELCOME || g_app.current_page == PAGE_FINISH) {
                RECT white_area = {168, 0, rc.right, kClientH - kFooterH};
                FillRect(hdc, &white_area, g_app.white_brush);
            } else {
                RECT header = {0, 0, rc.right, kHeaderH};
                FillRect(hdc, &header, g_app.white_brush);
                HPEN pen = CreatePen(PS_SOLID, 1, RGB(215, 215, 215));
                HGDIOBJ old = SelectObject(hdc, pen);
                MoveToEx(hdc, 0, kHeaderH, nullptr);
                LineTo(hdc, rc.right, kHeaderH);
                SelectObject(hdc, old);
                DeleteObject(pen);
            }

            HPEN fpen = CreatePen(PS_SOLID, 1, RGB(215, 215, 215));
            HGDIOBJ oldf = SelectObject(hdc, fpen);
            MoveToEx(hdc, 0, kClientH - kFooterH, nullptr);
            LineTo(hdc, rc.right, kClientH - kFooterH);
            SelectObject(hdc, oldf);
            DeleteObject(fpen);

            EndPaint(hwnd, &ps);
            return 0;
        }

        case WM_CTLCOLORSTATIC: {
            HDC hdc = reinterpret_cast<HDC>(wParam);
            HWND ctrl = reinterpret_cast<HWND>(lParam);
            bool white_bg = (g_app.current_page == PAGE_WELCOME || g_app.current_page == PAGE_FINISH ||
                             ctrl == g_app.header_title || ctrl == g_app.header_sub);
            if (white_bg) {
                SetBkMode(hdc, TRANSPARENT);
                return reinterpret_cast<LRESULT>(g_app.white_brush);
            }
            return DefWindowProcW(hwnd, msg, wParam, lParam);
        }

        case WM_COMMAND: {
            int id = LOWORD(wParam);
            if (id == IDC_CHK_ACCEPT) {
                UpdatePageChrome(g_app.current_page);
            } else if (id == IDC_BTN_BROWSE) {
                BrowseForDestination();
            } else if (id == IDC_BTN_BACK) {
                if (g_app.current_page > PAGE_WELCOME && g_app.current_page < PAGE_INSTALL) {
                    ShowPage(g_app.current_page - 1);
                }
            } else if (id == IDC_BTN_NEXT) {
                if (g_app.current_page < PAGE_OPTIONS) {
                    ShowPage(g_app.current_page + 1);
                } else if (g_app.current_page == PAGE_OPTIONS) {
                    StartInstallWorker();
                } else if (g_app.current_page == PAGE_FINISH) {
                    if (g_app.install_succeeded) {
                        if (SendMessageW(g_app.chk_open_term, BM_GETCHECK, 0, 0) == BST_CHECKED) {
                            std::wstring arx_exe = (fs::path(g_app.installed_dir) / L"bin" / L"arx.exe").wstring();
                            std::wstring cmd = L"/K \"\"" + arx_exe + L"\" --version\"";
                            ShellExecuteW(nullptr, L"open", L"cmd.exe", cmd.c_str(), g_app.installed_dir.c_str(), SW_SHOWNORMAL);
                        }
                        if (SendMessageW(g_app.chk_open_guide, BM_GETCHECK, 0, 0) == BST_CHECKED) {
                            std::wstring guide = (fs::path(g_app.installed_dir) / L"docs" / L"GUIDE.md").wstring();
                            ShellExecuteW(nullptr, L"open", guide.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
                        }
                    }
                    DestroyWindow(hwnd);
                }
            } else if (id == IDC_BTN_CANCEL) {
                if (!g_app.installing) {
                    if (MessageBoxW(hwnd, L"Exit Aerix Setup?", L"Aerix Setup",
                                    MB_YESNO | MB_ICONQUESTION) == IDYES) {
                        DestroyWindow(hwnd);
                    }
                }
            }
            return 0;
        }

        case WM_INSTALL_PROGRESS:
            SendMessageW(g_app.progress_bar, PBM_SETPOS, wParam, 0);
            return 0;

        case WM_INSTALL_LOG: {
            auto* text = reinterpret_cast<std::wstring*>(lParam);
            if (text) {
                SetWindowTextW(g_app.lbl_status, text->c_str());
                AppendLogLine(*text);
                delete text;
            }
            return 0;
        }

        case WM_INSTALL_DONE: {
            bool ok = (wParam != 0);
            if (!ok) {
                ShowWindow(g_app.chk_open_term, SW_HIDE);
                ShowWindow(g_app.chk_open_guide, SW_HIDE);
                std::wstring msg = L"Installation failed:\r\n\r\n" + g_app.last_error;
                SetWindowTextW(g_app.lbl_finish_body, msg.c_str());
            }
            ShowPage(PAGE_FINISH);
            return 0;
        }

        case WM_CLOSE:
            if (g_app.installing) return 0;
            if (g_app.current_page == PAGE_FINISH ||
                MessageBoxW(hwnd, L"Exit Aerix Setup?", L"Aerix Setup", MB_YESNO | MB_ICONQUESTION) == IDYES) {
                DestroyWindow(hwnd);
            }
            return 0;

        case WM_DESTROY:
            if (g_app.white_brush) DeleteObject(g_app.white_brush);
            if (g_app.bmp_side) DeleteObject(g_app.bmp_side);
            if (g_app.bmp_banner) DeleteObject(g_app.bmp_banner);
            if (g_app.font_ui) DeleteObject(g_app.font_ui);
            if (g_app.font_bold) DeleteObject(g_app.font_bold);
            if (g_app.font_title) DeleteObject(g_app.font_title);
            if (g_app.font_mono) DeleteObject(g_app.font_mono);
            PostQuitMessage(0);
            return 0;
    }
    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

int HandleUninstallFlow(HINSTANCE, const CliArgs& cli) {
    std::wstring target = !cli.dir_override.empty() ? cli.dir_override : ResolveInstalledDirFromRegistry();
    if (target.empty()) {
        wchar_t exe_buf[MAX_PATH] = {};
        if (GetModuleFileNameW(nullptr, exe_buf, MAX_PATH) > 0) {
            target = fs::path(exe_buf).parent_path().wstring();
        }
    }

    if (!cli.silent) {
        std::wstring prompt = L"Are you sure you want to completely remove Aerix from:\n\n" + target + L"?";
        if (MessageBoxW(nullptr, prompt.c_str(), L"Aerix Uninstall", MB_YESNO | MB_ICONQUESTION) != IDYES) {
            return 0;
        }
    }

    std::wstring err;
    bool ok = RunUninstall(target, nullptr, err);
    wchar_t exe_buf[MAX_PATH] = {};
    if (GetModuleFileNameW(nullptr, exe_buf, MAX_PATH) > 0) {
        std::wstring exe_w(exe_buf);
        if (ToLowerW(fs::path(exe_w).parent_path().wstring()) == ToLowerW(target)) {
            ScheduleSelfDeleteAndDirCleanup(exe_w, target);
        }
    }

    if (!cli.silent) {
        if (ok) {
            MessageBoxW(nullptr, L"Aerix was successfully removed from your computer.",
                        L"Aerix Uninstall", MB_OK | MB_ICONINFORMATION);
        } else {
            MessageBoxW(nullptr, err.c_str(), L"Aerix Uninstall Error", MB_OK | MB_ICONERROR);
        }
    }
    return ok ? 0 : 1;
}

int HandleSilentInstall(HINSTANCE hinst, const CliArgs& cli) {
    InstallOptions opts;
    opts.install_dir = cli.dir_override.empty() ? GetDefaultInstallDir() : cli.dir_override;
    opts.configure_env = !cli.no_path;
    opts.file_associations = !cli.no_assoc;
    opts.install_vscode = !cli.no_vscode && !DetectVSCodeCli().empty();
    opts.install_antigravity = !cli.no_antigravity && !DetectAntigravityCli().empty();

    std::wstring err;
    bool ok = RunInstall(hinst, opts, nullptr, err);
    return ok ? 0 : 1;
}

}  // namespace

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE, LPSTR, int nCmdShow) {
    CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    INITCOMMONCONTROLSEX icc{sizeof(icc), ICC_PROGRESS_CLASS | ICC_STANDARD_CLASSES};
    InitCommonControlsEx(&icc);

    CliArgs cli = ParseCommandLine();
    if (cli.uninstall) {
        int rc = HandleUninstallFlow(hInstance, cli);
        CoUninitialize();
        return rc;
    }
    if (cli.silent) {
        int rc = HandleSilentInstall(hInstance, cli);
        CoUninitialize();
        return rc;
    }

    g_app.hinst = hInstance;
    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.hIcon = LoadIconW(hInstance, MAKEINTRESOURCEW(IDI_APP_ICON));
    wc.hIconSm = LoadIconW(hInstance, MAKEINTRESOURCEW(IDI_APP_ICON));
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    wc.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_BTNFACE + 1);
    wc.lpszClassName = L"AerixSetupWizardWnd";
    RegisterClassExW(&wc);

    DWORD style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
    RECT wr = {0, 0, kClientW, kClientH};
    AdjustWindowRectEx(&wr, style, FALSE, 0);
    int win_w = wr.right - wr.left;
    int win_h = wr.bottom - wr.top;

    RECT work{};
    SystemParametersInfoW(SPI_GETWORKAREA, 0, &work, 0);
    int pos_x = work.left + ((work.right - work.left) - win_w) / 2;
    int pos_y = work.top + ((work.bottom - work.top) - win_h) / 2;

    HWND hwnd = CreateWindowExW(
        0, wc.lpszClassName,
        L"Setup - Aerix Native Systems Language " AERIX_VERSION_WSTR,
        style, pos_x, pos_y, win_w, win_h,
        nullptr, nullptr, hInstance, nullptr);

    ShowWindow(hwnd, nCmdShow);
    UpdateWindow(hwnd);

    MSG msg;
    while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
        if (!IsDialogMessageW(hwnd, &msg)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }

    CoUninitialize();
    return g_app.install_succeeded ? 0 : 0;
}
