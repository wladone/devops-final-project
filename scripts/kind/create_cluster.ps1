param (
    [string]$ClusterName = "dq-gitops",
    [string]$ConfigPath = "lab/kind/cluster-config.yaml",
    [string]$RegistryContainer = "dq-lab-registry"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$kindConfig = Join-Path $repoRoot $ConfigPath
. (Join-Path $repoRoot "scripts\common.ps1")
Add-ProjectBinToPath

docker ps --format "{{.Names}}" | Select-String -SimpleMatch $RegistryContainer | Out-Null
if (-not $?) {
    powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\lab\start.ps1")
}

$kindClusters = & kind get clusters
if ($kindClusters -contains $ClusterName) {
    Write-Host "kind cluster '$ClusterName' already exists." -ForegroundColor Yellow
}
else {
    & kind create cluster --config $kindConfig
}

$registryConnected = $false
try {
    $kindNetwork = docker network inspect kind | ConvertFrom-Json
    if ($kindNetwork -and $kindNetwork[0].Containers) {
        foreach ($container in $kindNetwork[0].Containers.PSObject.Properties.Value) {
            if ($container.Name -eq $RegistryContainer) {
                $registryConnected = $true
                break
            }
        }
    }
}
catch {
    $registryConnected = $false
}

if (-not $registryConnected) {
    docker network connect kind $RegistryContainer | Out-Null
}

$localRegistryConfig = @"
apiVersion: v1
kind: ConfigMap
metadata:
  name: local-registry-hosting
  namespace: kube-public
data:
  localRegistryHosting.v1: |
    host: "localhost:5001"
    help: "https://kind.sigs.k8s.io/docs/user/local-registry/"
"@

$localRegistryConfig | kubectl apply -f -
kubectl config use-context "kind-$ClusterName" | Out-Null

Write-Host "kind cluster '$ClusterName' is ready and using registry localhost:5001." -ForegroundColor Green
