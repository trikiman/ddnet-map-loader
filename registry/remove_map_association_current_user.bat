@echo off
setlocal
REM Safe cleanup: ONLY .map for current user + our app OpenWith entries.

REM Remove per-user .map ProgID and class
reg delete "HKCU\Software\Classes\.map" /f >nul 2>&1
reg delete "HKCU\Software\Classes\DDNetMapFile" /f >nul 2>&1

REM Remove our app from OpenWith Apps (if present)
reg delete "HKCU\Software\Classes\Applications\ddnet_control.exe" /f >nul 2>&1
reg delete "HKCU\Software\Classes\Applications\ddnet_control_v2.exe" /f >nul 2>&1

REM Clear Explorer per-extension history for .map
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.map\UserChoice" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.map\OpenWithList" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.map\OpenWithProgids" /f >nul 2>&1

echo [OK] Removed .map association entries for current user.
echo Restart Windows Explorer (Task Manager -> Windows Explorer -> Restart) to refresh UI.
endlocal
