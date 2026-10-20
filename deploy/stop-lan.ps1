<#
stop-lan.ps1: stops what start-lan.ps1 started on this laptop: Caddy (443/8443, the LAN door first), the console
(3000) and the API (8000). Docker Desktop, the database and Ollama keep running (other work uses them too).
Start again with deploy\start-lan.ps1, or sign out and in (the "ITI AI LAN" task).
#>

$Root = Split-Path -Parent $PSScriptRoot
$RunLog = Join-Path $Root "data\logs\start-lan.log"

function Log([string]$text) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $text
    Add-Content -Path $RunLog -Value $line -Encoding utf8 -ErrorAction SilentlyContinue
    Write-Host $line
}

Log "=== stop-lan.ps1 (user $env:USERNAME)"
foreach ($stop in @(@("Caddy", 443), @("Caddy", 8443), @("console", 3000), @("API", 8000))) {
    $name, $port = $stop
    $owners = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($id in $owners) {
        $process = Get-Process -Id $id -ErrorAction SilentlyContinue
        if ($process) {
            try {
                Stop-Process -Id $id -Force -ErrorAction Stop
                Log ("stopped {0} on {1} ({2}, pid {3})" -f $name, $port, $process.ProcessName, $id)
            } catch {
                # e.g. it was started from an administrator window: stop it there (Ctrl+C) or from an admin PowerShell
                Log ("COULD NOT stop {0} on {1} ({2}, pid {3}): {4}" -f $name, $port, $process.ProcessName, $id, $_.Exception.Message)
            }
        }
    }
}
Log "=== stopped (Docker, the database and Ollama are still running)"
