@echo off
setlocal ENABLEDELAYEDEXPANSION
echo Fixing DDNet Map Loader v2 file association...

REM Resolve repo root
set ROOT=%~dp0
if "%ROOT:~-1%"=="\" set ROOT=%ROOT:~0,-1%

set EXE_PATH=%ROOT%\ddnet_control.exe
set ICON_PATH=%ROOT%\Image\ddnet_loader.ico
if not exist "%ICON_PATH%" set ICON_PATH=%ROOT%\ddnet_loader.ico

echo Registering .map with: %EXE_PATH%

REM 1. Create .map ProgID and handlers under HKCU (No admin required)
reg add "HKCU\Software\Classes\.map" /ve /d "DDNetMapFile" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile" /ve /d "DDNet Map File" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\DefaultIcon" /ve /d "%ICON_PATH%" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\shell" /ve /d "open" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\shell\open" /ve /d "Open" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\shell\open\command" /ve /d "\"%EXE_PATH%\" \"%%1\"" /f >nul

REM 2. Add to "Open With" list and Application registration
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.map\OpenWithProgids" /v "DDNetMapFile" /t REG_NONE /f >nul
reg add "HKCU\Software\Classes\Applications\ddnet_control.exe" /v "FriendlyAppName" /t REG_SZ /d "DDNet Map Loader" /f >nul
reg add "HKCU\Software\Classes\Applications\ddnet_control.exe\DefaultIcon" /ve /t REG_SZ /d "%ICON_PATH%" /f >nul
reg add "HKCU\Software\Classes\Applications\ddnet_control.exe\shell\open\command" /ve /t REG_SZ /d "\"%EXE_PATH%\" \"%%1\"" /f >nul

REM 3. Force Windows to refresh file associations
echo Refreshing Windows Explorer and Icon Cache...
ie4uinit.exe -show

REM Clear icon cache (requires restart of explorer)
taskkill /f /im explorer.exe >nul 2>&1
del /f /q "%localappdata%\IconCache.db" >nul 2>&1
start explorer.exe

echo.
echo [OK] File association setup complete!
echo.
echo If icons still don't show correctly, you may need to:
echo 1. Right-click a .map file -> Properties -> Change -> Select DDNet Map Loader
echo 2. Restart your computer
echo.
pause
endlocal