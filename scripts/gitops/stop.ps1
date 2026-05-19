param ()

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$composeFile = Join-Path $repoRoot "lab\gitops\docker-compose.yml"

docker compose -f $composeFile down --remove-orphans

Write-Host "Local GitOps git daemon stopped." -ForegroundColor Yellow
