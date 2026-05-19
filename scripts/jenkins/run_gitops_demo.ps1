param (
    [string]$JobName = "data-quality-monitor-local",
    [string]$BaseUrl = "http://localhost:8080",
    [string]$CloneDir = ".tmp\\jenkins-gitops-source",
    [string]$LocalBareRepo = "lab\\gitops\\repos\\data-quality-monitor.git",
    [string]$ContainerGitRemote = "git://host.docker.internal:9418/data-quality-monitor.git",
    [string]$RegistryImage = "localhost:5001/data-quality-monitor",
    [string]$GitOpsValuesFile = "helm/data-quality-monitor/values-kind-local.yaml",
    [string]$K8sNamespace = "dq-monitor-dev",
    [string]$K8sRunnerCronJob = "data-quality-monitor-data-quality-monitor-runner",
    [string]$K8sDashboardResource = "svc/data-quality-monitor-data-quality-monitor-dashboard",
    [string]$DashboardUrl = "http://host.docker.internal:28501",
    [bool]$RefreshJob = $false,
    [int]$TimeoutSeconds = 1200
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$preparedSource = & (Join-Path $repoRoot "scripts\jenkins\prepare_gitops_source.ps1") `
    -CloneDir $CloneDir `
    -LocalBareRepo $LocalBareRepo `
    -ContainerGitRemote $ContainerGitRemote
$clonePath = $preparedSource.ClonePath
$bareRepoPath = $preparedSource.BareRepoPath

if ($RefreshJob) {
    & (Join-Path $repoRoot "scripts\jenkins\create_job.ps1") -JobName $JobName -BaseUrl $BaseUrl
}

$projectDirInContainer = $preparedSource.ContainerProjectDir

$commonBuildArgs = @{
    JobName = $JobName
    BaseUrl = $BaseUrl
    ProjectDir = $projectDirInContainer
    RegistryImage = $RegistryImage
    RunHelmValidation = $true
    HelmValuesFile = $GitOpsValuesFile
    HelmNamespace = $K8sNamespace
    K8sNamespace = $K8sNamespace
    K8sRunnerCronJob = $K8sRunnerCronJob
    K8sDashboardResource = $K8sDashboardResource
    RunTerraformValidate = $false
    RunSecurityScan = $false
    RunGitOpsUpdate = $true
    GitOpsValuesFile = $GitOpsValuesFile
    GitOpsTargetBranch = "main"
    GitOpsPushRemote = "origin"
    RunArgoCdSync = $true
    ArgoCdAppName = "data-quality-monitor-kind"
    ArgoCdSyncMode = "core"
    ArgoCdNamespace = "argocd"
    DashboardUrl = $DashboardUrl
    SkipCheckout = $true
    WaitForCompletion = $true
    TimeoutSeconds = $TimeoutSeconds
}

try {
    & (Join-Path $repoRoot "scripts\jenkins\build_job.ps1") @commonBuildArgs
}
catch {
    Write-Host "First Jenkins run failed, retrying once to bypass the inline-pipeline checkout quirk..." -ForegroundColor Yellow
    & (Join-Path $repoRoot "scripts\jenkins\build_job.ps1") @commonBuildArgs
}

$expectedRevision = (git --git-dir=$bareRepoPath rev-parse main).Trim()

$syncDeadline = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Seconds 5
    $app = kubectl get application data-quality-monitor-kind -n argocd -o json | ConvertFrom-Json
    $syncRevision = $app.status.sync.revision
    $syncStatus = $app.status.sync.status
    $healthStatus = $app.status.health.status
    if ($syncRevision -eq $expectedRevision -and $syncStatus -eq "Synced" -and $healthStatus -eq "Healthy") {
        break
    }
} while ((Get-Date) -lt $syncDeadline)

$finalApp = kubectl get application data-quality-monitor-kind -n argocd -o json | ConvertFrom-Json
if ($finalApp.status.sync.revision -ne $expectedRevision -or $finalApp.status.sync.status -ne "Synced" -or $finalApp.status.health.status -ne "Healthy") {
    throw "Argo CD did not sync the expected Git revision $expectedRevision in time."
}

$deployedImage = kubectl get deployment data-quality-monitor-data-quality-monitor-dashboard -n $K8sNamespace -o jsonpath="{.spec.template.spec.containers[0].image}"
Write-Host "Argo CD synced revision $expectedRevision" -ForegroundColor Green
Write-Host "Kubernetes dashboard image: $deployedImage" -ForegroundColor Cyan

Write-Host "Jenkins GitOps demo run completed." -ForegroundColor Green
