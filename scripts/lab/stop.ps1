param ()

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$tfDir = Join-Path $repoRoot "terraform\environments\lab"

if (-not (Test-Path (Join-Path $tfDir ".terraform"))) {
    Write-Host "Terraform state for the lab is not initialized — nothing to destroy." -ForegroundColor Yellow
    return
}

Write-Host "Destroying Terraform-managed lab resources..." -ForegroundColor Cyan
terraform -chdir="$tfDir" destroy -auto-approve

Write-Host "Local DevOps lab stopped." -ForegroundColor Yellow
