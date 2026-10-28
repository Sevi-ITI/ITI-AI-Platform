<#
start-lan.ps1: starts the ITI AI Platform for the office network, in order, in the background (no windows).

  1. Docker Desktop -> waits until the engine answers                    (Docker Desktop starts at sign-in by itself)
  2. The stack      -> `docker compose -f deploy/docker-compose.yaml up -d` (postgres, ollama, migrate, api, game;
                       caddy too if deploy\.env has COMPOSE_PROFILES=model,door), waits for the API and the console
                       (game-ui, :4000) to answer (they run in containers since 9.5.8; admin-ui retired 2026-10-28)
  3. Caddy          -> the native Caddy, the only door to the LAN (443 console, 8443 API), only if nothing holds 443
                       yet (the Caddy container stays off until the office PCs trust our root: 9.5.5)

Safe to run again at any time: a piece that is already running is left alone. The containers also come back by
themselves after a restart (restart: unless-stopped); only the native Caddy needs this script. Logs (git-ignored):
  data\logs\start-lan.log   what this script did, with times
  data\logs\caddy-<date>.log (+ .err.log)   the native Caddy's own output
  the containers: docker compose -f deploy/docker-compose.yaml logs --tail 50 <service>

Runs as the signed-in user ON PURPOSE: the native Caddy's certificate authority lives in this user's profile
(%AppData%\Caddy); another account (a Windows service) would make a NEW root certificate.
Take the platform off the network with deploy\stop-lan.ps1. Never add --remove-orphans to compose here: the dev records
container shares the project "deploy".
#>

# "Continue", not "Stop": Windows PowerShell 5.1 would stop on any line a program writes to its error output.
# Failures are thrown on purpose below instead.
$ErrorActionPreference = "Continue"
$Name = "ITI-Vinas.ho.intellismartinc.com"    # Caddy answers only to its configured names
$Root = Split-Path -Parent $PSScriptRoot            # the repository root (this file is in deploy\)
$Compose = Join-Path $Root "deploy\docker-compose.yaml"
$Logs = Join-Path $Root "data\logs"
$Day = Get-Date -Format "yyyyMMdd"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
$RunLog = Join-Path $Logs "start-lan.log"

function Log([string]$text) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $text
    Add-Content -Path $RunLog -Value $line -Encoding utf8
    Write-Host $line
}

function Listening([int]$port) {
    [bool](Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
}

function Http-Ok([string]$url) {
    # curl.exe -k: Caddy's own certificate is not in this laptop's trust store, and that is fine for a local check.
    # --resolve: the laptop's name points at 127.0.0.1 for this check only (Caddy answers only to its names).
    $code = & curl.exe -s -k -o NUL --max-time 5 --resolve "${Name}:443:127.0.0.1" --resolve "${Name}:8443:127.0.0.1" `
        -w "%{http_code}" $url 2>$null
    return ($code -eq "200")
}

function Wait-For([string]$what, [int]$seconds, [scriptblock]$ready) {
    $until = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $until) {
        if (& $ready) { Log "  ok: $what"; return }
        Start-Sleep -Seconds 3
    }
    throw "$what did not come up within $seconds s (see data\logs and docker compose logs)"
}

try {
    Log "=== start-lan.ps1 (user $env:USERNAME)"

    # 1. Docker Desktop
    if (-not (& docker info --format "{{.ServerVersion}}" 2>$null)) {
        if (-not (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue)) {
            Log "1. starting Docker Desktop"
            Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        } else { Log "1. Docker Desktop is starting" }
        Wait-For "Docker engine" 240 { [bool](& docker info --format "{{.ServerVersion}}" 2>$null) }
    } else { Log "1. Docker is running" }

    # 2. The stack (compose leaves running containers alone; migrate runs once and exits)
    Log "2. docker compose up -d"
    & docker compose -f $Compose up -d 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed: run it by hand to see why" }
    Wait-For "API /health" 300 { Http-Ok "http://127.0.0.1:8000/health" }
    Wait-For "console /login" 120 { Http-Ok "http://127.0.0.1:4000/login" }

    # 3. The native Caddy: the only door to the office network (443 console, 8443 API)
    if (-not (Listening 443)) {
        Log "3. starting the native Caddy"
        Start-Process -FilePath "C:\Tools\caddy\caddy.exe" -ArgumentList "run --config deploy\Caddyfile" -WorkingDirectory $Root `
            -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Logs "caddy-$Day.log") `
            -RedirectStandardError (Join-Path $Logs "caddy-$Day.err.log") | Out-Null
    } else { Log "3. something already serves 443 (the native Caddy, or the Caddy container)" }
    Wait-For "Caddy on 443 and 8443" 60 { (Http-Ok "https://${Name}/login") -and (Http-Ok "https://${Name}:8443/health") }

    Log "=== all up: https://$Name (console), https://${Name}:8443/v1/docs (API docs), http://127.0.0.1:4000 (console, this laptop)"
}
catch {
    Log "!!! FAILED: $($_.Exception.Message)"
    exit 1
}
