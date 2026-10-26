<#
start-lan.ps1: starts the ITI AI Platform for the office network, in order, in the background (no windows).

  1. Docker Desktop -> waits until the Postgres container is healthy   (Docker Desktop starts at sign-in by itself)
  2. Ollama         -> waits until it answers on 127.0.0.1:11434       (Ollama starts at sign-in by itself)
  3. API (uvicorn)  -> waits for http://127.0.0.1:8000/health
  4. Console        -> `npm start` (the BUILT console), waits for http://127.0.0.1:3000/login
  5. Caddy          -> the only door to the LAN (443 testers, 8443 API), waits for https on 443
  6. Game console   -> `npm start` in game-ui (the BUILT app), waits for http://127.0.0.1:4000/login (this laptop
                       only: Caddy does not open it to the LAN)

Safe to run again at any time: a piece that is already running is left alone. Logs (git-ignored):
  data\logs\start-lan.log   what this script did, with times
  data\logs\api-<date>.log, console-<date>.log, caddy-<date>.log, game-console-<date>.log (+ .err.log): each
  service's own output

Started at sign-in by the Task Scheduler task "ITI AI LAN" (see System Guide 16.4). Runs as the signed-in user ON
PURPOSE: Caddy's certificate authority lives in this user's profile (%AppData%\Caddy); another account (a Windows
service) would make a NEW root certificate that the office PCs don't trust.
Stop the API, both consoles and Caddy with deploy\stop-lan.ps1.
#>

# "Continue", not "Stop": Windows PowerShell 5.1 would stop on any line a program writes to its error output.
# Failures are thrown on purpose below instead.
$ErrorActionPreference = "Continue"
$Name = "ITI-Vinas.ho.intellismartinc.com"    # Caddy answers only to its configured names
$Root = Split-Path -Parent $PSScriptRoot            # the repository root (this file is in deploy\)
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
    throw "$what did not come up within $seconds s (see the logs in data\logs)"
}

function Start-Hidden([string]$name, [string]$exe, [string]$arguments, [string]$folder) {
    Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $folder -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $Logs "$name-$Day.log") `
        -RedirectStandardError (Join-Path $Logs "$name-$Day.err.log") | Out-Null
}

try {
    Log "=== start-lan.ps1 (user $env:USERNAME)"

    # 1. Docker Desktop and the database
    if (-not (& docker info --format "{{.ServerVersion}}" 2>$null)) {
        if (-not (Get-Process "Docker Desktop" -ErrorAction SilentlyContinue)) {
            Log "1. starting Docker Desktop"
            Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        } else { Log "1. Docker Desktop is starting" }
        Wait-For "Docker engine" 240 { [bool](& docker info --format "{{.ServerVersion}}" 2>$null) }
    } else { Log "1. Docker is running" }
    & docker compose -f (Join-Path $Root "deploy\docker-compose.dev.yaml") up -d 2>&1 | Out-Null
    Wait-For "Postgres (healthy)" 180 { (& docker inspect -f "{{.State.Health.Status}}" deploy-postgres-1 2>$null) -eq "healthy" }

    # 2. Ollama (the models)
    if (-not (Listening 11434)) {
        if (-not (Get-Process "ollama app" -ErrorAction SilentlyContinue)) {
            Log "2. starting Ollama"
            Start-Process (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama app.exe")
        }
        Wait-For "Ollama on 11434" 120 { Http-Ok "http://127.0.0.1:11434" }
    } else { Log "2. Ollama is running" }

    # 3. The API (one process, no --reload: the answer queue lives in the process)
    if (-not (Listening 8000)) {
        Log "3. starting the API"
        $backend = Join-Path $Root "backend"
        Start-Hidden "api" (Join-Path $backend ".venv\Scripts\python.exe") "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" $backend
        Wait-For "API /health" 90 { Http-Ok "http://127.0.0.1:8000/health" }
    } else { Log "3. the API is running" }

    # 4. The console (the built app: after a code change run `npm run build` in admin-ui first)
    if (-not (Listening 3000)) {
        $ui = Join-Path $Root "admin-ui"
        if (-not (Test-Path (Join-Path $ui ".next\BUILD_ID"))) { throw "the console is not built: run 'npm run build' in admin-ui" }
        Log "4. starting the console"
        Start-Hidden "console" "C:\Program Files\nodejs\npm.cmd" "start" $ui
        Wait-For "console /login" 90 { Http-Ok "http://127.0.0.1:3000/login" }
    } else { Log "4. the console is running" }

    # 5. Caddy: the only door to the office network (443 testers, 8443 API)
    if (-not (Listening 443)) {
        Log "5. starting Caddy"
        Start-Hidden "caddy" "C:\Tools\caddy\caddy.exe" "run --config deploy\Caddyfile" $Root
        Wait-For "Caddy on 443 and 8443" 60 { (Http-Ok "https://${Name}/login") -and (Http-Ok "https://${Name}:8443/health") }
    } else { Log "5. Caddy is running" }

    # 6. The game console (the built app: after a code change run `npm run build` in game-ui first)
    if (-not (Listening 4000)) {
        $game = Join-Path $Root "game-ui"
        if (-not (Test-Path (Join-Path $game ".next\BUILD_ID"))) { throw "the game console is not built: run 'npm run build' in game-ui" }
        Log "6. starting the game console"
        Start-Hidden "game-console" "C:\Program Files\nodejs\npm.cmd" "start" $game
        Wait-For "game console /login" 90 { Http-Ok "http://127.0.0.1:4000/login" }
    } else { Log "6. the game console is running" }

    Log "=== all up: https://$Name (testers), https://${Name}:8443/v1/docs (API docs), http://127.0.0.1:4000 (game console, this laptop)"
}
catch {
    Log "!!! FAILED: $($_.Exception.Message)"
    exit 1
}
