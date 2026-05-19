$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

Push-Location $repoRoot
try {
    docker compose --env-file jenkins/.env -f jenkins/docker-compose.yml down
}
finally {
    Pop-Location
}

