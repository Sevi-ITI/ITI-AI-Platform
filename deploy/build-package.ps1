<#
build-package.ps1: makes ITI-AI-Package (step 9.5.7) from the images that run now, in one command.

  1. tags iti-ai-api, iti-ai-console and iti-ai-game :dev (the tested builds) as :<Tag>
  2. copies the files a machine needs into C:\Users\ITI-Vinas\Documents\ITI-AI-Package (next to the repo, never in it):
     README.md, deploy\ (compose file, Caddyfile, .env.example, check-cert.ps1), backend\.env.example, data\uploads\
  3. docker save: all six images into ITI-AI-Package-<Tag>.tar (about 4 GB; about 12 GB once loaded)

Usage (repo root):  powershell -NoProfile -ExecutionPolicy Bypass -File deploy\build-package.ps1 -Tag 2026.10.27
Then check it:      docker load -i C:\Users\ITI-Vinas\Documents\ITI-AI-Package\ITI-AI-Package-<Tag>.tar  (six lines)
No secrets go in: only the .env.example files, never .env, root.key, documents or the database.
#>
param([Parameter(Mandatory = $true)][string]$Tag)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Out = "C:\Users\ITI-Vinas\Documents\ITI-AI-Package"
$Ours = "iti-ai-api", "iti-ai-console", "iti-ai-game"
$Theirs = "pgvector/pgvector:0.8.7-pg17", "ollama/ollama:0.35.0", "caddy:2.11.7"   # the pins in docker-compose.yaml

foreach ($image in $Ours) {
    & docker tag "${image}:dev" "${image}:$Tag"
    if ($LASTEXITCODE -ne 0) { throw "${image}:dev not found: build the stack first" }
}

New-Item -ItemType Directory -Force "$Out\deploy", "$Out\backend", "$Out\data\uploads" | Out-Null
Copy-Item (Join-Path $Root "deploy\docker-compose.yaml"), (Join-Path $Root "deploy\Caddyfile"),
    (Join-Path $Root "deploy\.env.example"), (Join-Path $Root "deploy\check-cert.ps1") "$Out\deploy" -Force
Copy-Item (Join-Path $Root "backend\.env.example") "$Out\backend" -Force
Copy-Item (Join-Path $Root "deploy\PACKAGE-README.md") "$Out\README.md" -Force

$tar = Join-Path $Out "ITI-AI-Package-$Tag.tar"
Write-Host "saving six images to $tar (a few minutes)"
& docker save -o $tar ($Ours | ForEach-Object { "${_}:$Tag" }) $Theirs
if ($LASTEXITCODE -ne 0) { throw "docker save failed" }
Write-Host ("done: {0:N1} GB" -f ((Get-Item $tar).Length / 1GB))
