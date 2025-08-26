@echo off
setlocal
REM Removes user-scope association for .map related to this portable package.

REM ProgID cleanup
reg delete "HKCU\Software\Classes\DDNetMapFile" /f >nul 2>nul

REM FileExts cleanup (OpenWith caches)
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.map\OpenWithProgids" /v "DDNetMapFile" /f >nul 2>nul

REM If .map default points to our ProgID, clear it (SAFE: only changes HKCU)
for /f "tokens=3*" %%A in ('reg query "HKCU\Software\Classes\.map" /ve 2^>nul ^| findstr /i "REG_SZ"') do set CUR=%%A %%B
if /i "%CUR%"=="DDNetMapFile" reg delete "HKCU\Software\Classes\.map" /ve /f >nul 2>nul

REM Applications entry (Open With entry)
reg delete "HKCU\Software\Classes\Applications\ddnet_control.exe" /f >nul 2>nul

echo [OK] Removed user-scope .map association for DDNet Map Loader.
endlocal
