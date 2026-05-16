# make_cert.ps1 — generate a self-signed cert for ddnet_control's web server.
# Uses pure .NET `CertificateRequest` so it works in PowerShell 5.1 and 7+.
# No admin required. Writes web/cert.pem + web/key.pem next to web/server.py.

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$out  = Join-Path $root 'web'
if (-not (Test-Path $out)) {
    Write-Host "[ERR] $out does not exist." -ForegroundColor Red
    exit 1
}

$certPath = Join-Path $out 'cert.pem'
$keyPath  = Join-Path $out 'key.pem'

if ((Test-Path $certPath) -and (Test-Path $keyPath)) {
    Write-Host "Cert already exists at:"
    Write-Host "  $certPath"
    Write-Host "  $keyPath"
    Write-Host "Delete both files and re-run if you want to regenerate."
    exit 0
}

# Subject Alternative Names: localhost, loopback, and primary LAN IPv4.
$names = @('localhost', '127.0.0.1')
try {
    $primaryIp = Get-NetIPAddress -AddressFamily IPv4 `
        -PrefixOrigin Dhcp,Manual -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '169.*' -and $_.IPAddress -notlike '127.*' } |
        Select-Object -First 1 -ExpandProperty IPAddress
    if ($primaryIp) { $names += $primaryIp }
} catch { }

Write-Host "Subject Alternative Names: $($names -join ', ')"
Write-Host "Generating self-signed cert (valid 5 years)..."

$rsa = [System.Security.Cryptography.RSA]::Create(2048)
try {
    $dn  = New-Object System.Security.Cryptography.X509Certificates.X500DistinguishedName('CN=ddnet-control')
    $hashAlg = [System.Security.Cryptography.HashAlgorithmName]::SHA256
    $padding = [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
    $req = New-Object System.Security.Cryptography.X509Certificates.CertificateRequest($dn, $rsa, $hashAlg, $padding)

    # SAN: IPs as IPAddress entries, DNS names as DNS entries
    $san = New-Object System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder
    foreach ($n in $names) {
        $parsedIp = $null
        if ([System.Net.IPAddress]::TryParse($n, [ref]$parsedIp)) {
            $san.AddIpAddress($parsedIp)
        } else {
            $san.AddDnsName($n)
        }
    }
    $req.CertificateExtensions.Add($san.Build())

    # Extended Key Usage: id-kp-serverAuth (1.3.6.1.5.5.7.3.1)
    $ekuOids = New-Object System.Security.Cryptography.OidCollection
    [void]$ekuOids.Add((New-Object System.Security.Cryptography.Oid('1.3.6.1.5.5.7.3.1')))
    $req.CertificateExtensions.Add((New-Object System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension($ekuOids, $false)))

    # Basic Constraints: not a CA
    $req.CertificateExtensions.Add((New-Object System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($false, $false, 0, $false)))

    # Key Usage: digitalSignature + keyEncipherment
    $ku = [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment
    $req.CertificateExtensions.Add((New-Object System.Security.Cryptography.X509Certificates.X509KeyUsageExtension($ku, $false)))

    $notBefore = [DateTimeOffset]::Now.AddDays(-1)
    $notAfter  = [DateTimeOffset]::Now.AddYears(5)
    $cert = $req.CreateSelfSigned($notBefore, $notAfter)

    try {
        $certB64 = [Convert]::ToBase64String($cert.RawData, 'InsertLineBreaks')
        $keyB64  = [Convert]::ToBase64String($rsa.ExportPkcs8PrivateKey(), 'InsertLineBreaks')

        Set-Content -Path $certPath -Value "-----BEGIN CERTIFICATE-----`n$certB64`n-----END CERTIFICATE-----" -Encoding ASCII
        Set-Content -Path $keyPath  -Value "-----BEGIN PRIVATE KEY-----`n$keyB64`n-----END PRIVATE KEY-----"  -Encoding ASCII
    } finally {
        $cert.Dispose()
    }
} finally {
    $rsa.Dispose()
}

Write-Host ""
Write-Host "[OK] cert.pem + key.pem written to $out" -ForegroundColor Green
Write-Host "Restart web/server.py and it will pick up HTTPS automatically."
