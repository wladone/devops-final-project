param (
    [string]$Namespace = "devtroncd",
    [string]$ReleaseName = "devtron",
    [switch]$OpenPortForward
)

$ErrorActionPreference = "Stop"

Write-Host "Installing Devtron OSS into namespace '$Namespace'..." -ForegroundColor Cyan
helm repo add devtron https://helm.devtron.ai --force-update | Out-Null
helm repo update devtron | Out-Null

kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f - | Out-Null
helm upgrade --install $ReleaseName devtron/devtron-operator --namespace $Namespace --create-namespace --wait --timeout 15m

Write-Host "Devtron install submitted. Checking pods..." -ForegroundColor Cyan
kubectl get pods -n $Namespace

if ($OpenPortForward) {
    & (Join-Path $PSScriptRoot "port_forward.ps1") -Namespace $Namespace
}

Write-Host ""
Write-Host "Devtron OSS is optional for this demo. It gives us a Kubernetes app-management UI on top of the same kind cluster." -ForegroundColor Green
Write-Host "Run scripts/devtron/port_forward.ps1, then open the printed localhost URL." -ForegroundColor Yellow
