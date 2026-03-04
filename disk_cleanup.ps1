# Disk Space Analyzer for C: drive
Write-Host "=== DISK SPACE ANALYSIS ===" -ForegroundColor Cyan

# Get disk info
$disk = Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='C:'"
$freeGB = [math]::Round($disk.FreeSpace / 1GB, 2)
$totalGB = [math]::Round($disk.Size / 1GB, 2)
$usedGB = $totalGB - $freeGB
Write-Host "Total: $totalGB GB | Used: $usedGB GB | Free: $freeGB GB" -ForegroundColor Yellow

Write-Host "`n=== LARGE FOLDERS TO CHECK ===" -ForegroundColor Cyan

# Function to get folder size
function Get-FolderSize($path) {
    if (Test-Path $path) {
        $size = (Get-ChildItem $path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue).Sum
        return [math]::Round($size / 1GB, 2)
    }
    return 0
}

# Check common large folders
$folders = @(
    "$env:LOCALAPPDATA\Temp",
    "$env:TEMP",
    "C:\Windows\Temp",
    "$env:LOCALAPPDATA\Microsoft\Windows\Explorer",
    "$env:LOCALAPPDATA\npm-cache",
    "$env:LOCALAPPDATA\pip\Cache",
    "$env:LOCALAPPDATA\NuGet\Cache",
    "$env:USERPROFILE\Downloads",
    "$env:USERPROFILE\.cache",
    "$env:LOCALAPPDATA\Docker",
    "$env:LOCALAPPDATA\Programs",
    "$env:APPDATA\npm-cache",
    "C:\Windows\SoftwareDistribution\Download"
)

foreach ($folder in $folders) {
    if (Test-Path $folder) {
        $size = Get-FolderSize $folder
        if ($size -gt 0.1) {
            Write-Host "$folder : $size GB" -ForegroundColor $(if($size -gt 1){"Red"}else{"White"})
        }
    }
}

Write-Host "`n=== RECYCLE BIN ===" -ForegroundColor Cyan
$shell = New-Object -ComObject Shell.Application
$recycleBin = $shell.NameSpace(0x0a)
$recycleBinItems = $recycleBin.Items()
Write-Host "Items in Recycle Bin: $($recycleBinItems.Count)"

Write-Host "`n=== QUICK CLEANUP OPTIONS ===" -ForegroundColor Green
Write-Host "1. Empty Recycle Bin: Clear-RecycleBin -Force"
Write-Host "2. Clear Temp files: Remove-Item `$env:TEMP\* -Recurse -Force -ErrorAction SilentlyContinue"
Write-Host "3. Clear Windows Temp: Remove-Item C:\Windows\Temp\* -Recurse -Force -ErrorAction SilentlyContinue"
Write-Host "4. Run Disk Cleanup: cleanmgr /d C"
Write-Host "5. Clear npm cache: npm cache clean --force"
Write-Host "6. Clear pip cache: pip cache purge"
