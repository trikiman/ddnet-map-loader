@echo off
REM Thin wrapper around make_cert.ps1.
REM Prefer PowerShell 7+ (pwsh) — its .NET runtime has ExportPkcs8PrivateKey.
REM Falls back to Windows PowerShell 5.1 (powershell) only if pwsh is missing.

where /q pwsh
if %ERRORLEVEL% EQU 0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_cert.ps1"
    exit /b %ERRORLEVEL%
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0make_cert.ps1"
exit /b %ERRORLEVEL%
