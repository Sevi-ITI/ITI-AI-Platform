<#
stop-lan.ps1: takes the ITI AI Platform off the office network: the native Caddy (443/8443, the LAN door) first, then
the containers that answer people: caddy (if on), game (the console) and api. The database and Ollama keep running (other
work uses them too). Start again with deploy\start-lan.ps1.

Since 9.5.8 (2026-10-27) the API and the console run in containers: they are stopped with `docker compose stop`, never
by killing their port's owner (com.docker.backend is ALL of Docker, 2026-10-26). Stopped containers stay stopped after
a restart until start-lan.ps1 (compose up) starts them again.
#>

$Root = Split-Path -Parent $PSScriptRoot
$RunLog = Join-Path $Root "data\logs\start-lan.log"

function Log([string]$text) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $text
    Add-Content -Path $RunLog -Value $line -Encoding utf8 -ErrorAction SilentlyContinue
    Write-Host $line
}

Log "=== stop-lan.ps1 (user $env:USERNAME)"

# 1. The native Caddy (only caddy.exe: a port held by Docker is left to step 2)
foreach ($port in 443, 8443) {
    $owners = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($id in $owners) {
        $process = Get-Process -Id $id -ErrorAction SilentlyContinue
        if ($process -and $process.ProcessName -eq "caddy") {
            try {
                Stop-Process -Id $id -Force -ErrorAction Stop
                Log ("stopped the native Caddy on {0} (pid {1})" -f $port, $id)
            } catch {
                # e.g. it was started from an administrator window: stop it there (Ctrl+C) or from an admin PowerShell
                Log ("COULD NOT stop the native Caddy on {0} (pid {1}): {2}" -f $port, $id, $_.Exception.Message)
            }
        }
    }
}

# 2. The containers that answer people (caddy is skipped by compose when its profile is off)
& docker compose -f (Join-Path $Root "deploy\docker-compose.yaml") stop caddy game api 2>&1 | Out-Null
Log "stopped the containers caddy (if on), game, api"
Log "=== stopped (Docker, the database and Ollama are still running)"
