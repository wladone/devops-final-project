param (
    [string]$ReleaseName = "kube-prometheus-stack",
    [string]$Namespace = "monitoring",
    [string]$ValuesFile = "lab/kind/monitoring-values.yaml",
    [int]$TimeoutSeconds = 900
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
. (Join-Path $repoRoot "scripts\common.ps1")
Add-ProjectBinToPath

$valuesPath = Join-Path $repoRoot $ValuesFile
if (-not (Test-Path $valuesPath)) {
    throw "Monitoring values file not found: $valuesPath"
}

kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f - | Out-Null

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>$null | Out-Null
helm repo update | Out-Null

helm upgrade --install $ReleaseName prometheus-community/kube-prometheus-stack `
    --namespace $Namespace `
    --create-namespace `
    --values $valuesPath `
    --wait `
    --timeout "$($TimeoutSeconds)s" | Out-Null

kubectl rollout status deployment/$ReleaseName-grafana -n $Namespace --timeout "$($TimeoutSeconds)s" | Out-Null

Write-Host "Prometheus and Grafana are ready in namespace '$Namespace'." -ForegroundColor Green
Write-Host "Grafana service: $ReleaseName-grafana" -ForegroundColor Cyan
Write-Host "Prometheus service: $ReleaseName-prometheus" -ForegroundColor Cyan
