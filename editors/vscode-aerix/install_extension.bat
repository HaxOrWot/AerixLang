@echo off
set "SCRIPT_DIR=%~dp0"
echo ==================================================================
echo         AERIX LANGUAGE EXTENSION MANUAL INSTALLER
echo ==================================================================
echo.
echo [*] Installing Aerix Language extension into Visual Studio Code...
call code --install-extension "%SCRIPT_DIR%aerix.vsix" --force
echo.
echo [*] Installing Aerix Language extension into Google Antigravity IDE...
call antigravity --install-extension "%SCRIPT_DIR%aerix.vsix" --force
echo.
echo ==================================================================
echo  [SUCCESS] Aerix extension installed into both VS Code & Antigravity!
echo ==================================================================
pause
