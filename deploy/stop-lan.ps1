<#
stop-lan.ps1: stops what start-lan.ps1 started on this laptop: Caddy (443/8443, the LAN door first), the console
(3000), the game console (4000) and the API (8000). Docker Desktop, the database and Ollama keep running (other work uses them too).
Start again with deploy\start-lan.ps1, or sign out and in (the "ITI AI LAN" task).

Only stops node, python and caddy: the programs start-lan.ps1 starts. A port served by a Docker container shows
Docker's own process (com.docker.backend) as its owner, and stopping that takes ALL of Docker down (2026-10-26).
Those are left running and named in the log; stop containers with `docker compose -f deploy/docker-compose.yaml stop`.
#>

$Root = Split-Path -Parent $PSScriptRoot
$RunLog = Join-Path $Root "data\logs\start-lan.log"

function Log([string]$text) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $text
    Add-Content -Path $RunLog -Value $line -Encoding utf8 -ErrorAction SilentlyContinue
    Write-Host $line
}

$Ours = @("node", "python", "caddy")   # process names start-lan.ps1 starts; anything else is left alone

Log "=== stop-lan.ps1 (user $env:USERNAME)"
foreach ($stop in @(@("Caddy", 443), @("Caddy", 8443), @("console", 3000), @("game console", 4000), @("API", 8000))) {
    $name, $port = $stop
    $owners = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($id in $owners) {
        $process = Get-Process -Id $id -ErrorAction SilentlyContinue
        if ($process -and $Ours -notcontains $process.ProcessName) {
            Log ("left {0} on {1} running ({2}, pid {3}: not started by start-lan; Docker? use docker compose stop)" -f $name, $port, $process.ProcessName, $id)
        } elseif ($process) {
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
Log "=== stopped (Docker, its containers, the database and Ollama are still running)"
