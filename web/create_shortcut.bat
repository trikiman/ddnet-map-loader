@echo off
cd /d "%~dp0"
echo Creating DDNet Map Manager shortcut on desktop...

:: Use pythonw.exe (windowless Python) so no console window is needed.
:: Falls back to python.exe if pythonw.exe is not found.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$desktop = $ws.SpecialFolders('Desktop');" ^
  "$lnk = $ws.CreateShortcut(\"$desktop\DDNet Map Manager.lnk\");" ^
  "$pydir = Split-Path (Get-Command python -ErrorAction SilentlyContinue).Source;" ^
  "$pythonw = if ($pydir -and (Test-Path (Join-Path $pydir 'pythonw.exe'))) { Join-Path $pydir 'pythonw.exe' } else { 'python.exe' };" ^
  "$lnk.TargetPath = $pythonw;" ^
  "$lnk.Arguments = '\"E:\Projects\ddnetcontrol\web\server.py\"';" ^
  "$lnk.WorkingDirectory = 'E:\Projects\ddnetcontrol\web';" ^
  "$lnk.IconLocation = 'E:\Projects\ddnetcontrol\web\map.ico';" ^
  "$lnk.Description = 'DDNet Map Manager';" ^
  "$lnk.WindowStyle = 1;" ^
  "$lnk.Save();" ^
  "Write-Output ('Shortcut target: ' + $lnk.TargetPath);"

if %ERRORLEVEL% equ 0 (
    echo Shortcut created successfully on Desktop!
    echo Run it once - if tray icon appears, right-click it to open the browser.
    echo If no tray icon, open http://localhost:8299 manually in your browser.
) else (
    echo Failed to create shortcut.
)
pause
