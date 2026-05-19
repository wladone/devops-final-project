param (
    [string]$Version = "v2.13.3"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$kubeconfig = Join-Path $HOME ".kube\config"
. (Join-Path $repoRoot "scripts\common.ps1")
Add-ProjectBinToPath

Push-Location (Join-Path $repoRoot "terraform\environments\dev")
try {
    terraform init | Out-Null
    terraform apply -auto-approve -var "kubeconfig_path=$kubeconfig" | Out-Null
}
finally {
    Pop-Location
}

kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f - | Out-Null
kubectl apply -n argocd -f "https://raw.githubusercontent.com/argoproj/argo-cd/$Version/manifests/install.yaml" | Out-Null

kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s
kubectl wait --for=condition=available deployment/argocd-repo-server -n argocd --timeout=300s
kubectl rollout status statefulset/argocd-application-controller -n argocd --timeout=300s

Write-Host "Argo CD is installed in the cluster." -ForegroundColor Green
