@echo off
setlocal ENABLEDELAYEDEXPANSION
REM Associates .map files with this portable folder (Current User). No admin required.

REM Resolve portable root (this .bat is in ddnet-map-loader-v2.0.0\registry)
set REGDIR=%~dp0
set ROOT=%REGDIR%..
for %%I in ("%ROOT%") do set ROOT=%%~fI

set EXE_PATH=%ROOT%\ddnet_control.exe
set ICON_PATH=%ROOT%\ddnet_loader.ico
if not exist "%ICON_PATH%" set ICON_PATH=%EXE_PATH%,0

REM Create ProgID and set as default for .map
reg add "HKCU\Software\Classes\.map" /ve /d "DDNetMapFile" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile" /ve /d "DDNet Map File" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\DefaultIcon" /ve /d "%ICON_PATH%" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\shell" /ve /d "open" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\shell\open" /ve /d "Open" /f >nul
reg add "HKCU\Software\Classes\DDNetMapFile\shell\open\command" /ve /d "\"%EXE_PATH%\" \"%1\"" /f >nul

REM Ensure it appears in Open With
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.map\OpenWithProgids" /v "DDNetMapFile" /t REG_NONE /f >nul
reg add "HKCU\Software\Classes\Applications\ddnet_control.exe" /v "FriendlyAppName" /t REG_SZ /d "DDNet Map Loader" /f >nul
reg add "HKCU\Software\Classes\Applications\ddnet_control.exe\DefaultIcon" /ve /t REG_SZ /d "%ICON_PATH%" /f >nul
reg add "HKCU\Software\Classes\Applications\ddnet_control.exe\shell\open\command" /ve /t REG_SZ /d "\"%EXE_PATH%\" \"%1\"" /f >nul

echo [OK] .map associated with: %EXE_PATH%
echo Icon: %ICON_PATH%
echo Restart Windows Explorer (Task Manager -> Windows Explorer -> Restart) if icons/dialog don\'t update.
endlocal
