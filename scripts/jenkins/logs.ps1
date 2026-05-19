$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Push-Location $repoRoot
try {
    docker compose --env-file jenkins/.env -f jenkins/docker-compose.yml logs --tail=100
}
finally {
    Pop-Location
}

