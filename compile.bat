@echo off
setlocal enableextensions
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"

echo === Setting up MSVC environment ===
set "VSDEVCMD="
if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" (
  for /f "usebackq delims=" %%I in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -find Common7\Tools\VsDevCmd.bat`) do (
    set "VSDEVCMD=%%I"
  )
)
if not defined VSDEVCMD if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat" (
  set "VSDEVCMD=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat"
)
if not defined VSDEVCMD if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" (
  set "VSDEVCMD=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat"
)
if not defined VSDEVCMD (
  echo [ERROR] Could not locate VsDevCmd.bat.
  popd & exit /b 1
)
for %%I in ("%VSDEVCMD%") do set "VSDEVCMD_DIR=%%~dpI"
set "VSENV_HELPER=%TEMP%\ddnetcontrol-vsenv-%RANDOM%.cmd"
> "%VSENV_HELPER%" echo @echo off
>> "%VSENV_HELPER%" echo call "%VSDEVCMD%" -no_logo -no_ext -arch=amd64 -host_arch=amd64 ^>nul
>> "%VSENV_HELPER%" echo if errorlevel 1 exit /b 1
>> "%VSENV_HELPER%" echo call "%VSDEVCMD_DIR%..\..\VC\Auxiliary\Build\vcvars64.bat" ^>nul
>> "%VSENV_HELPER%" echo if errorlevel 1 exit /b 1
>> "%VSENV_HELPER%" echo set
for /f "usebackq delims=" %%I in (`cmd /d /c ""%VSENV_HELPER%"" ^| findstr /R "^[A-Za-z_][A-Za-z0-9_()]*="`) do set "%%I"
if exist "%VSENV_HELPER%" del "%VSENV_HELPER%"
if errorlevel 1 (
  echo [ERROR] Failed to initialize Visual Studio build environment.
  popd & exit /b 1
)

echo === Resource compile ===
rc /nologo ddnet_control.rc
if errorlevel 1 (
  echo [ERROR] Resource compilation failed.
  popd & exit /b 1
)

echo === C++ compile and link ===
cl /nologo /EHsc /std:c++20 ddnet_control.cpp ddnet_control.res ^
  /link ws2_32.lib ole32.lib shell32.lib /SUBSYSTEM:WINDOWS /out:ddnet_control.exe
if errorlevel 1 (
  echo [ERROR] C++ compilation/link failed.
  popd & exit /b 1
)

echo [OK] Build succeeded: %SCRIPT_DIR%ddnet_control.exe
popd
endlocal
