@echo off
REM DDNet Map Manager — debug launcher.
REM Runs the server in a visible console, logs everything to
REM %APPDATA%\DDNet\maps\map-manager-debug.log, and pauses on exit
REM so you can read any crash message.

setlocal enableextensions
cd /d "%~dp0"

set "LOG=%APPDATA%\DDNet\maps\map-manager-debug.log"
if not exist "%APPDATA%\DDNet\maps" mkdir "%APPDATA%\DDNet\maps" >nul 2>&1

echo ================================================================
echo  DDNet Map Manager debug launcher
echo  Log file: %LOG%
echo  Press Ctrl+C in this window to stop the server.
echo ================================================================
echo.

REM Print to the console AND tee everything to the log via a temp wrapper
python -u server.py 2>&1 > "%LOG%" 2>&1
set "EXITCODE=%ERRORLEVEL%"

echo.
echo ================================================================
echo  Server exited with code %EXITCODE%
echo  Last 40 lines of the log:
echo ================================================================
powershell -NoProfile -Command "Get-Content -Path $env:LOG -Tail 40"
echo ================================================================
echo.
pause
