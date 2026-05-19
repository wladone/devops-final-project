$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$jenkinsDir = Join-Path $repoRoot "jenkins"
$envFile = Join-Path $jenkinsDir ".env"
$exampleEnvFile = Join-Path $jenkinsDir ".env.example"
$tmpDir = Join-Path $repoRoot ".tmp"
$jenkinsKubeconfig = Join-Path $tmpDir "jenkins-kubeconfig"

if (-not (Test-Path $envFile)) {
    Copy-Item $exampleEnvFile $envFile
}

New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
$rawKubeconfig = kubectl config view --raw
if (-not $rawKubeconfig) {
    throw "Could not read the current kubeconfig via kubectl."
}
$containerFriendlyKubeconfig = $rawKubeconfig `
    -replace 'server: https://127\.0\.0\.1:', 'server: https://host.docker.internal:' `
    -replace 'server: https://localhost:', 'server: https://host.docker.internal:' `
    -replace '(?m)^(\s*)certificate-authority-data: .+$', '$1insecure-skip-tls-verify: true'
Set-Content -Path $jenkinsKubeconfig -Value $containerFriendlyKubeconfig -Encoding UTF8

Push-Location $repoRoot
try {
    docker compose --env-file jenkins/.env -f jenkins/docker-compose.yml up -d --build
    Write-Host "Jenkins is starting at http://localhost:8080" -ForegroundColor Green
    Write-Host "SonarQube is starting at http://localhost:9000" -ForegroundColor Green
    Write-Host "Default login comes from jenkins/.env" -ForegroundColor Cyan
}
finally {
    Pop-Location
}
