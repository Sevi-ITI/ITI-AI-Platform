# check-cert.ps1: does a Caddy port's certificate chain up to the root the office PCs trust? Public data only.
# Usage (repo root): powershell -NoProfile -ExecutionPolicy Bypass -File deploy\check-cert.ps1 -Port 443
param([int]$Port = 443, [string]$Name = "ITI-Vinas.ho.intellismartinc.com")
$Trusted = "65A7AD4E59B2386A1597FF82A953E151F33F1594"   # Caddy Local Authority - 2026 ECC Root (System Guide 16.4)
$script:sent = @()
$tcp = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $Port)
$ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, {
    param($s, $cert, $chain, $errors)
    $script:sent = @($chain.ChainElements | ForEach-Object { New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($_.Certificate) })
    $true
})
$ssl.AuthenticateAsClient($Name)
$ssl.Dispose(); $tcp.Dispose()
$root = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("$env:APPDATA\Caddy\pki\authorities\local\root.crt")
$chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
$chain.ChainPolicy.RevocationMode = "NoCheck"
$chain.ChainPolicy.VerificationFlags = "AllowUnknownCertificateAuthority"
$chain.ChainPolicy.ExtraStore.Add($root) | Out-Null
$script:sent | Select-Object -Skip 1 | ForEach-Object { $chain.ChainPolicy.ExtraStore.Add($_) | Out-Null }
$ok = $chain.Build($script:sent[0])
$top = $chain.ChainElements[$chain.ChainElements.Count - 1].Certificate
"port {0}: certificate for {1}, valid to {2}" -f $Port, $script:sent[0].GetNameInfo("DnsName", $false), $script:sent[0].NotAfter.ToString("yyyy-MM-dd HH:mm")
"  chain: " + (($chain.ChainElements | ForEach-Object { if ($_.Certificate.Subject) { $_.Certificate.Subject } else { "(site)" } }) -join "  ->  ")
"  same root as the office PCs trust: {0}" -f ($ok -and $top.Thumbprint -eq $Trusted)