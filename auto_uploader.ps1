param(
    [Parameter(Mandatory=$true)][string]$File,
    [Parameter(Mandatory=$true)][string]$Server,
    [Parameter(Mandatory=$false)][string]$Token
)

# Normalize server URL (no trailing slash)
if ($Server.EndsWith('/')) { $Server = $Server.TrimEnd('/') }

if (!(Test-Path -LiteralPath $File)) {
    Write-Host "File not found: $File" -ForegroundColor Red
    exit 1
}

Write-Host "Watching: $File" -ForegroundColor Cyan
Write-Host "Server:   $Server" -ForegroundColor Cyan
if ($Token) { Write-Host "Token:    $Token" -ForegroundColor Cyan }

Add-Type -AssemblyName System.Net.Http
$handler = New-Object System.Net.Http.HttpClientHandler
$client  = New-Object System.Net.Http.HttpClient($handler)
$client.Timeout = [TimeSpan]::FromSeconds(120)

if ($Token) {
    $client.DefaultRequestHeaders.Add('X-Upload-Token', $Token)
}

function Upload-Map {
    param([string]$Path)

    try {
        if (!(Test-Path -LiteralPath $Path)) { return }
        $fileInfo = Get-Item -LiteralPath $Path -ErrorAction Stop
        $stream = $fileInfo.OpenRead()

        $content = New-Object System.Net.Http.MultipartFormDataContent
        $fileContent = New-Object System.Net.Http.StreamContent($stream)
        $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('application/octet-stream')
        # field name must be 'file'
        $content.Add($fileContent, 'file', $fileInfo.Name)

        $uri = "$Server/upload"
        $resp = $client.PostAsync($uri, $content).GetAwaiter().GetResult()
        $text = $resp.Content.ReadAsStringAsync().GetAwaiter().GetResult()

        if ($resp.IsSuccessStatusCode) {
            Write-Host "[upload] $($fileInfo.Name) -> OK : $text" -ForegroundColor Green
        } else {
            Write-Host "[upload] $($fileInfo.Name) -> FAIL ($($resp.StatusCode)) : $text" -ForegroundColor Red
        }
    } catch {
        Write-Host "[upload] error: $($_.Exception.Message)" -ForegroundColor Red
    } finally {
        if ($stream) { $stream.Dispose() }
        if ($content) { $content.Dispose() }
    }
}

# Capture the function for use inside event runspace as a proper ScriptBlock
$uploadFn = ${function:Upload-Map}.GetNewClosure()

# Do an initial upload
& $uploadFn -Path $File

# Set up a watcher with debounce
$fsw = New-Object System.IO.FileSystemWatcher
$fsw.Path = [System.IO.Path]::GetDirectoryName($File)
$fsw.Filter = [System.IO.Path]::GetFileName($File)
$fsw.NotifyFilter = [System.IO.NotifyFilters]::LastWrite -bor [System.IO.NotifyFilters]::FileName -bor [System.IO.NotifyFilters]::Size
$fsw.IncludeSubdirectories = $false
$fsw.EnableRaisingEvents = $true

$debounceMs = 500
# Use tick-based debounce to avoid DateTime subtraction issues in event scope
$script:lastTicks = 0L

# Use automatic $Event variable to access the changed path reliably
$action = {
    try {
        $nowTicks = [DateTime]::UtcNow.Ticks
        if ($script:lastTicks -ne 0 -and (($nowTicks - $script:lastTicks) / 10000) -lt $script:debounceMs) { return }
        $script:lastTicks = $nowTicks
        $path = $Event.SourceEventArgs.FullPath
        if ($path -like '*.toberemoved') { return }
        Write-Host "[watch] change detected: $path" -ForegroundColor Yellow
        Start-Sleep -Milliseconds 200 # brief delay to allow writer to release the file
        $upload = $Event.MessageData
        & $upload -Path $path
    } catch {
        Write-Host "[watch] handler error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

$createdReg = Register-ObjectEvent $fsw Created -Action $action -MessageData $uploadFn
$changedReg = Register-ObjectEvent $fsw Changed -Action $action -MessageData $uploadFn
$renamedReg = Register-ObjectEvent $fsw Renamed -Action $action -MessageData $uploadFn

Write-Host "Auto-uploading on save... Press Ctrl+C to stop." -ForegroundColor Yellow
try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    if ($createdReg) { Unregister-Event -SourceIdentifier $createdReg.Name }
    if ($changedReg) { Unregister-Event -SourceIdentifier $changedReg.Name }
    if ($renamedReg) { Unregister-Event -SourceIdentifier $renamedReg.Name }
    if ($fsw) { $fsw.Dispose() }
    if ($client) { $client.Dispose() }
}
