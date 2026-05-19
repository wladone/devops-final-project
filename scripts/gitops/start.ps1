param ()

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$composeFile = Join-Path $repoRoot "lab\gitops\docker-compose.yml"
$reposDir = Join-Path $repoRoot "lab\gitops\repos"

New-Item -ItemType Directory -Path $reposDir -Force | Out-Null
docker compose -f $composeFile up -d --remove-orphans

Write-Host "Local GitOps git daemon is running on git://localhost:9418" -ForegroundColor Green
