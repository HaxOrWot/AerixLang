#!/usr/bin/env sh
# Aerix (arx) - Universal Linux & macOS Installer
# Usage:
#   curl -fsSL https://get.aerix-lang.org/install.sh | sh
#   or locally: ./install.sh

set -e

echo ""
echo "=========================================================="
echo "    ___         _      "
echo "   / _ \___ ___(_)_ __ "
echo "  / __ / -_) __/ /\ \ /"
echo " /_/ |_\__/_/ /_//_\_\ "
echo " Aerix Programming Language - Universal POSIX Installer"
echo "=========================================================="
echo ""

AERIX_HOME="${HOME}/.aerix"
AERIX_BIN="${AERIX_HOME}/bin"
AERIX_STDLIB="${AERIX_HOME}/stdlib"

echo "[*] Target installation folder: ${AERIX_HOME}"
mkdir -p "${AERIX_BIN}" "${AERIX_STDLIB}"

# Check for local files or download
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_DIST="${SCRIPT_DIR}/dist/arx"
LOCAL_DIST_ARXC="${SCRIPT_DIR}/dist/arxc"
LOCAL_STDLIB="${SCRIPT_DIR}/stdlib/aerix_rt.h"

AERIX_REPO="${AERIX_REPO:-HaxOrWot/AerixLang}"
RELEASE_BASE="https://github.com/${AERIX_REPO}/releases/latest/download"
RAW_BASE="https://raw.githubusercontent.com/${AERIX_REPO}/main"

if [ -f "${LOCAL_DIST}" ]; then
    echo "[*] Installing local standalone toolchain from dist/arx..."
    cp "${LOCAL_DIST}" "${AERIX_BIN}/arx"
else
    echo "[*] Fetching latest Aerix binary from GitHub releases..."
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "${RELEASE_BASE}/arx-linux-x64" -o "${AERIX_BIN}/arx" || true
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "${AERIX_BIN}/arx" "${RELEASE_BASE}/arx-linux-x64" || true
    fi
fi

if [ -f "${LOCAL_DIST_ARXC}" ]; then
    echo "[*] Installing local standalone compiler from dist/arxc..."
    cp "${LOCAL_DIST_ARXC}" "${AERIX_BIN}/arxc"
else
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "${RELEASE_BASE}/arxc-linux-x64" -o "${AERIX_BIN}/arxc" || true
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "${AERIX_BIN}/arxc" "${RELEASE_BASE}/arxc-linux-x64" || true
    fi
fi

if [ -f "${LOCAL_STDLIB}" ]; then
    cp "${LOCAL_STDLIB}" "${AERIX_STDLIB}/aerix_rt.h"
    echo "[OK] Installed runtime stdlib to: ${AERIX_STDLIB}"
else
    echo "[*] Fetching runtime stdlib from GitHub..."
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "${RAW_BASE}/stdlib/aerix_rt.h" -o "${AERIX_STDLIB}/aerix_rt.h" || true
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "${AERIX_STDLIB}/aerix_rt.h" "${RAW_BASE}/stdlib/aerix_rt.h" || true
    fi
fi

# Ensure executable permissions
[ -f "${AERIX_BIN}/arx" ] && chmod +x "${AERIX_BIN}/arx"
[ -f "${AERIX_BIN}/arxc" ] && chmod +x "${AERIX_BIN}/arxc"

# Add to PATH in shell profile
SHELL_PROFILE=""
if [ -f "${HOME}/.zshrc" ]; then
    SHELL_PROFILE="${HOME}/.zshrc"
elif [ -f "${HOME}/.bashrc" ]; then
    SHELL_PROFILE="${HOME}/.bashrc"
elif [ -f "${HOME}/.profile" ]; then
    SHELL_PROFILE="${HOME}/.profile"
fi

PATH_LINE='export PATH="$HOME/.aerix/bin:$PATH"'
if [ -n "${SHELL_PROFILE}" ]; then
    if ! grep -q ".aerix/bin" "${SHELL_PROFILE}" 2>/dev/null; then
        echo "" >> "${SHELL_PROFILE}"
        echo "# Aerix Toolchain" >> "${SHELL_PROFILE}"
        echo "${PATH_LINE}" >> "${SHELL_PROFILE}"
        echo "[OK] Added Aerix to PATH in ${SHELL_PROFILE}"
    else
        echo "[OK] Aerix is already configured in ${SHELL_PROFILE}"
    fi
fi

# Run diagnostics if binary exists
if [ -x "${AERIX_BIN}/arx" ]; then
    echo ""
    "${AERIX_BIN}/arx" doctor || true
fi

echo ""
echo "=========================================================="
echo "[SUCCESS] Aerix has been successfully installed!"
echo "=========================================================="
echo "Get started in 3 steps:"
echo "  1. Restart your terminal or run: source ${SHELL_PROFILE:-~/.bashrc}"
echo "  2. arx new my_app"
echo "  3. cd my_app && arx run src/main.arx"
echo ""
