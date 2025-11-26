@echo off
echo Fixing DDNet Map Loader v2 file association...

REM Import registry settings
echo Importing registry settings...
reg import "c:\Users\rust-\CascadeProjects\ddnetcontrol\registry\set_map_association_current_user.reg"

REM Force Windows to refresh file associations
echo Refreshing file associations...
assoc .map=DDNetMapFile
ftype DDNetMapFile="c:\Users\rust-\CascadeProjects\ddnetcontrol\ddnet_control.exe" "%%1"

REM Refresh icon cache
echo Refreshing icon cache...
ie4uinit.exe -show

REM Clear icon cache (requires restart of explorer)
echo Clearing icon cache...
taskkill /f /im explorer.exe >nul 2>&1
del /f /q "%localappdata%\IconCache.db" >nul 2>&1
start explorer.exe

echo.
echo File association setup complete!
echo Please try double-clicking a .map file now.
echo.
echo If icons still don't show correctly, you may need to:
echo 1. Restart your computer, or
echo 2. Right-click a .map file -> Properties -> Change -> Select ddnet_control.exe
echo.
pause