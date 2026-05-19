param (
    [string]$AppManifest = "argocd\app-kind-local.yaml"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
. (Join-Path $repoRoot "scripts\common.ps1")
Add-ProjectBinToPath

& (Join-Path $repoRoot "scripts\gitops\bootstrap_local_repo.ps1")

$gitDaemonContainer = docker ps `
    --filter "label=com.docker.compose.project=gitops" `
    --filter "label=com.docker.compose.service=git-daemon" `
    --format "{{.Names}}" |
    Select-Object -First 1

if (-not $gitDaemonContainer) {
    throw "Could not find the running GitOps git daemon container."
}

$repoBridgeManifest = Join-Path $repoRoot ".tmp\gitops-repo-bridge.yaml"

$inspectData = docker inspect $gitDaemonContainer | ConvertFrom-Json
$gitDaemonIp = $inspectData[0].NetworkSettings.Networks.kind.IPAddress
if (-not $gitDaemonIp) {
    docker network connect kind $gitDaemonContainer 2>$null | Out-Null
    $inspectData = docker inspect $gitDaemonContainer | ConvertFrom-Json
    $gitDaemonIp = $inspectData[0].NetworkSettings.Networks.kind.IPAddress
}

if ($LASTEXITCODE -ne 0 -or -not $gitDaemonIp) {
    throw "Failed to resolve the Git daemon container IP on the kind network."
}

$repoBridgeYaml = @"
apiVersion: v1
kind: Service
metadata:
  name: gitops-repo
  namespace: argocd
spec:
  ports:
    - name: git
      port: 9418
      targetPort: 9418
---
apiVersion: v1
kind: Endpoints
metadata:
  name: gitops-repo
  namespace: argocd
subsets:
  - addresses:
      - ip: $gitDaemonIp
    ports:
      - name: git
        port: 9418
"@

New-Item -ItemType Directory -Path (Split-Path $repoBridgeManifest) -Force | Out-Null
Set-Content -Path $repoBridgeManifest -Value $repoBridgeYaml -Encoding ASCII
kubectl apply -f $repoBridgeManifest | Out-Null

kubectl apply -f (Join-Path $repoRoot "argocd\project.yaml") | Out-Null
kubectl apply -f (Join-Path $repoRoot $AppManifest) | Out-Null
kubectl annotate application data-quality-monitor-kind -n argocd argocd.argoproj.io/refresh=hard --overwrite | Out-Null

$maxAttempts = 60
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    $appJson = kubectl get application data-quality-monitor-kind -n argocd -o json
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to read application status from Kubernetes."
    }

    $app = $appJson | ConvertFrom-Json
    $syncStatus = $app.status.sync.status
    $healthStatus = $app.status.health.status

    if ($syncStatus -eq "Synced" -and $healthStatus -eq "Healthy") {
        Write-Host "Argo CD application data-quality-monitor-kind is synced and healthy." -ForegroundColor Green
        exit 0
    }

    Start-Sleep -Seconds 5
}

kubectl describe application data-quality-monitor-kind -n argocd
throw "Argo CD application data-quality-monitor-kind did not become Synced/Healthy within the timeout."
