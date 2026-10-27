# check-cert.ps1: does a Caddy port's certificate chain up to a given root (the one the users' PCs must trust)?
# Public data only. Usage (from the repo or package root):
#   powershell -NoProfile -ExecutionPolicy Bypass -File deploy\check-cert.ps1 -Port 443
#   ... -Port 443 -Name ai.example.local -RootFile .\root.crt     (another machine: its own name and root)
# The laptop's defaults: its DNS name and the native Caddy's root in %AppData% (thumbprint 65A7AD4E…1594).
# A Caddy container's own root: docker compose -f deploy/docker-compose.yaml cp caddy:/data/caddy/pki/authorities/local/root.crt .
param(
    [int]$Port = 443,
    [string]$Name = "ITI-Vinas.ho.intellismartinc.com",
    [string]$RootFile = "$env:APPDATA\Caddy\pki\authorities\local\root.crt"
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $RootFile)) { throw "root certificate not found: $RootFile (pass -RootFile)" }
if (-not (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)) {
    throw "nothing listens on port $Port on this machine: start Caddy first"
}
$root = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2((Resolve-Path $RootFile).Path)
$script:sent = @()
$tcp = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $Port)
$ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, {
    param($s, $cert, $chain, $errors)
    $script:sent = @($chain.ChainElements | ForEach-Object { New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($_.Certificate) })
    $true
})
$ssl.AuthenticateAsClient($Name)
$ssl.Dispose(); $tcp.Dispose()
$chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
$chain.ChainPolicy.RevocationMode = "NoCheck"
$chain.ChainPolicy.VerificationFlags = "AllowUnknownCertificateAuthority"
$chain.ChainPolicy.ExtraStore.Add($root) | Out-Null
$script:sent | Select-Object -Skip 1 | ForEach-Object { $chain.ChainPolicy.ExtraStore.Add($_) | Out-Null }
$ok = $chain.Build($script:sent[0])
$top = $chain.ChainElements[$chain.ChainElements.Count - 1].Certificate
"port {0}: certificate for {1}, valid to {2}" -f $Port, $script:sent[0].GetNameInfo("DnsName", $false), $script:sent[0].NotAfter.ToString("yyyy-MM-dd HH:mm")
"  chain: " + (($chain.ChainElements | ForEach-Object { if ($_.Certificate.Subject) { $_.Certificate.Subject } else { "(site)" } }) -join "  ->  ")
"  root: {0} ({1})" -f $root.Subject, $root.Thumbprint
"  chains to that root: {0}" -f ($ok -and $top.Thumbprint -eq $root.Thumbprint)
