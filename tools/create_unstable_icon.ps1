param(
    [string]$OutPath = "c:\\Users\\rust-\\CascadeProjects\\ddnetcontrol\\Image\\ddnet-unstable.ico"
)
Add-Type -AssemblyName System.Drawing

function New-BadgeBitmap {
    param([int]$Size = 32)
    $bmp = New-Object System.Drawing.Bitmap $Size, $Size, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = 'HighQuality'
    # Transparent background
    $g.Clear([System.Drawing.Color]::Transparent)

    # Base circle (gray) for visibility
    $baseBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 60, 60, 60))
    $g.FillEllipse($baseBrush, 0, 0, $Size-1, $Size-1)

    # Red badge circle at top-right
    $badgeSize = [int]([Math]::Max(6, $Size * 0.4))
    $badgeX = $Size - $badgeSize - 2
    $badgeY = 2
    $redBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 220, 40, 40))
    $g.FillEllipse($redBrush, $badgeX, $badgeY, $badgeSize, $badgeSize)

    # White letter U in center for "Unstable"
    $fontSize = [int]([Math]::Max(6, $Size * 0.5))
    $font = New-Object System.Drawing.Font 'Segoe UI Semibold', $fontSize, ([System.Drawing.FontStyle]::Bold), 'Pixel'
    $fmt = New-Object System.Drawing.StringFormat
    $fmt.Alignment = 'Center'
    $fmt.LineAlignment = 'Center'
    $white = [System.Drawing.Brushes]::White
    $g.DrawString('U', $font, $white, ([System.Drawing.RectangleF]::new(0,0,$Size,$Size)), $fmt)

    $g.Dispose()
    return $bmp
}

# Create a 32x32 icon (sufficient for testing)
$bmp = New-BadgeBitmap -Size 32
$hIcon = $bmp.GetHicon()
try {
    $icon = [System.Drawing.Icon]::FromHandle($hIcon)
    $dir = [System.IO.Path]::GetDirectoryName($OutPath)
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $fs = [System.IO.File]::Open($OutPath, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write)
    try { $icon.Save($fs) } finally { $fs.Dispose() }
}
finally {
    # Destroy icon handle to avoid GDI leak
    [System.Runtime.InteropServices.Marshal]::Release($hIcon) | Out-Null
    $bmp.Dispose()
}
Write-Host "Created icon: $OutPath"
