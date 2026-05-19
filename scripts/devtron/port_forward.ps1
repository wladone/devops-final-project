param (
    [string]$Namespace = "devtroncd",
    [int]$LocalPort = 28000
)

$ErrorActionPreference = "Stop"

$services = kubectl get svc -n $Namespace -o jsonpath="{range .items[*]}{.metadata.name}{'|'}{range .spec.ports[*]}{.port}{','}{end}{'\n'}{end}"
if ($LASTEXITCODE -ne 0) {
    throw "Could not list Devtron services in namespace '$Namespace'."
}

$candidate = $services -split "`n" |
    Where-Object { $_ -match "devtron" -and ($_ -match "\|80," -or $_ -match "\|8080,") } |
    Select-Object -First 1

if (-not $candidate) {
    throw "Could not discover a Devtron web service. Run scripts/devtron/status.ps1 to inspect services."
}

$serviceName = ($candidate -split "\|")[0]
$remotePort = if ($candidate -match "\|80,") { 80 } else { 8080 }

Write-Host "Forwarding Devtron service '$serviceName' to http://localhost:$LocalPort ..." -ForegroundColor Cyan
Write-Host "Keep this terminal open while using Devtron." -ForegroundColor Yellow
kubectl port-forward -n $Namespace "svc/$serviceName" "${LocalPort}:${remotePort}"
