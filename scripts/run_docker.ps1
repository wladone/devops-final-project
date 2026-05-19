$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker was not found. Install Docker Desktop first."
}

try {
    docker info --format "{{.ServerVersion}}" *> $null
}
catch {
    Write-Error "Docker CLI exists, but Docker Desktop is not running. Start Docker Desktop and try again."
}

docker compose up --build

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker Compose failed."
}
