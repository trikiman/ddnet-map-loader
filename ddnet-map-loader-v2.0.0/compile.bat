@echo off
setlocal enableextensions
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"

echo === Setting up MSVC environment ===
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 (
  echo [ERROR] Failed to initialize Visual Studio build environment.
  echo [INFO] Please adjust the path to vcvars64.bat in this script for your system.
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
  /link ws2_32.lib ole32.lib shell32.lib /out:ddnet_control.exe
if errorlevel 1 (
  echo [ERROR] C++ compilation/link failed.
  popd & exit /b 1
)

echo [OK] Build succeeded: %SCRIPT_DIR%ddnet_control.exe
popd
endlocal