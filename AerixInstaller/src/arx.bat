@echo off
if exist "%~dp0..\src\arx.py" (
    python "%~dp0..\src\arx.py" %*
    exit /b %ERRORLEVEL%
)
if exist "%~dp0src\arx.py" (
    python "%~dp0src\arx.py" %*
    exit /b %ERRORLEVEL%
)
echo [ERROR] Aerix compiler entrypoint arx.py not found!
exit /b 1
