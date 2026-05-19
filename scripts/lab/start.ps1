param ()

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$tfDir = Join-Path $repoRoot "terraform\environments\lab"

# Terraform owns the lifecycle of the lab Linux target and the local OCI registry.
# The legacy lab/docker-compose.yml is kept as documentation of the equivalent
# imperative bring-up but is no longer the active path.
Write-Host "Initializing Terraform (lab environment)..." -ForegroundColor Cyan
terraform -chdir="$tfDir" init -input=false -upgrade=false | Out-Null

Write-Host "Applying Terraform plan to create the lab machine + registry..." -ForegroundColor Cyan
terraform -chdir="$tfDir" apply -auto-approve

Write-Host ""
Write-Host "Local DevOps lab started." -ForegroundColor Green
Write-Host "Registry: http://localhost:5001" -ForegroundColor Cyan
Write-Host "Linux target SSH: localhost:2222 (user devops / pass devops123!)" -ForegroundColor Cyan
