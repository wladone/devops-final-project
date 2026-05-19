param (
    [string]$Namespace = "devtroncd"
)

$ErrorActionPreference = "Stop"

Write-Host "Devtron namespace:" -ForegroundColor Cyan
kubectl get namespace $Namespace

Write-Host ""
Write-Host "Devtron pods:" -ForegroundColor Cyan
kubectl get pods -n $Namespace -o wide

Write-Host ""
Write-Host "Devtron services:" -ForegroundColor Cyan
kubectl get svc -n $Namespace -o wide
