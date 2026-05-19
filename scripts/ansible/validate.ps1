param (
    [string]$InventoryPath = "ansible/inventory.ini",
    [string]$PlaybookPath = "ansible/playbook.yml",
    [string]$ContainerName = "data-quality-jenkins"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

$containerRunning = docker inspect -f "{{.State.Running}}" $ContainerName 2>$null
if ($LASTEXITCODE -ne 0 -or $containerRunning.Trim() -ne "true") {
    throw "Jenkins container '$ContainerName' is not running. Start it first with scripts/jenkins/start.ps1."
}

$command = "cd /workspace/data-quality-monitor && ansible-playbook -i $InventoryPath $PlaybookPath --syntax-check"

docker exec $ContainerName sh -lc $command
