@echo off
setlocal ENABLEDELAYEDEXPANSION
REM Associate .map with the SOURCE build (current user only)

REM Resolve repo root (this .bat is in registry\)
set REGDIR=%~dp0
set ROOT=%REGDIR%..
for %%I in ("%ROOT%") do set ROOT=%%~fI

set EXE_PATH=%ROOT%\ddnet_control.exe
set ICON_PATH=%ROOT%\Image\ddnet_loader_fixed.ico
if not exist "%ICON_PATH%" set ICON_PATH=%ROOT%\Image\ddnet_loader.ico

REM Create .map ProgID and handlers under HKCU
reg add "HKCU\Software\Classes\.map" /ve /d "DDNetMapFile" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile" /ve /d "DDNet Map File" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\DefaultIcon" /ve /d "%ICON_PATH%" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\shell" /ve /d "open" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\shell\open" /ve /d "Open" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\shell\open\command" /ve /d "\"%EXE_PATH%\" \"%1\"" /f >nul

REM Make sure it appears in Open With list: add OpenWithProgids entry and Applications registration
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.map\OpenWithProgids" /v "DDNetMapFile" /t REG_NONE /f >nul
reg add "HKCU\Software\Classes\Applications\ddnet_control.exe" /v "FriendlyAppName" /t REG_SZ /d "DDNet Map Loader" /f >nul
reg add "HKCU\Software\Classes\Applications\ddnet_control.exe\DefaultIcon" /ve /t REG_SZ /d "%ICON_PATH%" /f >nul
reg add "HKCU\Software\Classes\Applications\ddnet_control.exe\shell\open\command" /ve /t REG_SZ /d "\"%EXE_PATH%\" \"%1\"" /f >nul

echo [OK] .map associated with: %EXE_PATH%
echo Icon: %ICON_PATH%
echo If you don't see it in Explorer, restart Windows Explorer.
endlocal
