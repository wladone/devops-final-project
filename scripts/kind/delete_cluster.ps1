param (
    [string]$ClusterName = "dq-gitops"
)

$ErrorActionPreference = "Stop"
. (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")) "scripts\common.ps1")
Add-ProjectBinToPath
& kind delete cluster --name $ClusterName
Write-Host "Deleted kind cluster '$ClusterName'." -ForegroundColor Yellow
