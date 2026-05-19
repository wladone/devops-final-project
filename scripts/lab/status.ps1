param ()

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$tfDir = Join-Path $repoRoot "terraform\environments\lab"

if (Test-Path (Join-Path $tfDir ".terraform")) {
    Write-Host "Terraform state (lab environment):" -ForegroundColor Cyan
    terraform -chdir="$tfDir" output 2>$null
    Write-Host ""
}

Write-Host "Lab containers currently on the daemon:" -ForegroundColor Cyan
docker ps --filter "name=dq-lab" --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
