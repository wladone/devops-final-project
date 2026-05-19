param (
    [string]$JenkinsBaseUrl = "http://localhost:8080",
    [string]$SonarUrl = "http://localhost:9000",
    [string]$ArgoCdPassword = "",
    [string]$GrafanaPassword = "",
    [switch]$SkipJenkins,
    [switch]$SkipSonar,
    [switch]$SkipArgoCd,
    [switch]$SkipGrafana
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
. (Join-Path $repoRoot "scripts\jenkins\common.ps1")

function Get-SettingOrDefault {
    param (
        [hashtable]$Settings,
        [string]$Name,
        [string]$DefaultValue
    )

    if ($Settings.ContainsKey($Name) -and $Settings[$Name]) {
        return $Settings[$Name]
    }

    return $DefaultValue
}

function New-BasicAuthHeader {
    param (
        [string]$UserName,
        [string]$Password = ""
    )

    $pair = "{0}:{1}" -f $UserName, $Password
    $bytes = [System.Text.Encoding]::ASCII.GetBytes($pair)
    return @{ Authorization = "Basic $([Convert]::ToBase64String($bytes))" }
}

function ConvertTo-Base64 {
    param (
        [string]$Value
    )

    return [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($Value))
}

function Wait-ForKubectlDeployment {
    param (
        [string]$Namespace,
        [string]$DeploymentName,
        [int]$TimeoutSeconds = 180
    )

    kubectl rollout status "deployment/$DeploymentName" -n $Namespace --timeout "$($TimeoutSeconds)s" | Out-Null
}

function Invoke-KubectlMergePatch {
    param (
        [string]$Namespace,
        [string]$Resource,
        [hashtable]$PatchObject
    )

    $patchPath = Join-Path ([System.IO.Path]::GetTempPath()) ("dq-demo-patch-{0}.json" -f ([guid]::NewGuid()))
    try {
        $PatchObject | ConvertTo-Json -Compress | Set-Content -Path $patchPath -Encoding UTF8
        kubectl -n $Namespace patch $Resource --type merge --patch-file $patchPath | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "kubectl patch failed for $Namespace/$Resource."
        }
    }
    finally {
        Remove-Item -LiteralPath $patchPath -Force -ErrorAction SilentlyContinue
    }
}

function Set-ArgoCdAdminPassword {
    param (
        [string]$Password
    )

    kubectl get namespace argocd | Out-Null
    kubectl -n argocd get secret argocd-secret | Out-Null

    $hash = (& docker exec data-quality-jenkins argocd account bcrypt --password $Password 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $hash) {
        $hash = (& docker run --rm quay.io/argoproj/argocd:v2.13.3 argocd account bcrypt --password $Password)
    }

    $hash = ($hash | Select-Object -First 1).Trim()
    if (-not $hash) {
        throw "Could not generate an Argo CD bcrypt password hash."
    }

    $patchObject = @{
        data = @{
            "admin.password" = ConvertTo-Base64 $hash
            "admin.passwordMtime" = ConvertTo-Base64 ((Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"))
        }
    }
    Invoke-KubectlMergePatch -Namespace "argocd" -Resource "secret/argocd-secret" -PatchObject $patchObject
    kubectl -n argocd rollout restart deployment/argocd-server | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not restart the Argo CD server deployment."
    }
    Wait-ForKubectlDeployment -Namespace "argocd" -DeploymentName "argocd-server" -TimeoutSeconds 240
}

function Set-GrafanaAdminPassword {
    param (
        [string]$UserName,
        [string]$Password
    )

    kubectl get namespace monitoring | Out-Null
    kubectl -n monitoring get secret kube-prometheus-stack-grafana | Out-Null

    $patchObject = @{
        data = @{
            "admin-user" = ConvertTo-Base64 $UserName
            "admin-password" = ConvertTo-Base64 $Password
        }
    }
    Invoke-KubectlMergePatch -Namespace "monitoring" -Resource "secret/kube-prometheus-stack-grafana" -PatchObject $patchObject
    kubectl -n monitoring rollout restart deployment/kube-prometheus-stack-grafana | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Could not restart the Grafana deployment."
    }
    Wait-ForKubectlDeployment -Namespace "monitoring" -DeploymentName "kube-prometheus-stack-grafana" -TimeoutSeconds 240
}

$settings = Get-JenkinsSettings
$jenkinsUser = Get-SettingOrDefault -Settings $settings -Name "JENKINS_ADMIN_ID" -DefaultValue "admin"
$jenkinsPassword = Get-SettingOrDefault -Settings $settings -Name "JENKINS_ADMIN_PASSWORD" -DefaultValue "admin123!"
$sonarPassword = Get-SettingOrDefault -Settings $settings -Name "SONARQUBE_ADMIN_PASSWORD" -DefaultValue "admin123!"
$grafanaUser = Get-SettingOrDefault -Settings $settings -Name "GRAFANA_ADMIN_USER" -DefaultValue "admin"
if (-not $GrafanaPassword) {
    $GrafanaPassword = Get-SettingOrDefault -Settings $settings -Name "GRAFANA_ADMIN_PASSWORD" -DefaultValue "admin123!"
}
if (-not $ArgoCdPassword) {
    $ArgoCdPassword = Get-SettingOrDefault -Settings $settings -Name "ARGOCD_ADMIN_PASSWORD" -DefaultValue "admin123!"
}

if (-not $SkipJenkins) {
    Write-Host "Validating Jenkins demo login..." -ForegroundColor Cyan
    $authHeaders = Get-JenkinsAuthHeader -UserName $jenkinsUser -Password $jenkinsPassword
    $null = Get-JenkinsWebSessionContext -BaseUrl $JenkinsBaseUrl -AuthHeaders $authHeaders
    Write-Host "Jenkins login ready: $jenkinsUser / $jenkinsPassword" -ForegroundColor Green
}

if (-not $SkipSonar) {
    Write-Host "Setting up SonarQube demo account and Jenkins token..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\jenkins\bootstrap_sonar.ps1") `
        -BaseUrl $JenkinsBaseUrl `
        -SonarUrl $SonarUrl

    $sonarValidation = Invoke-RestMethod `
        -Uri "$SonarUrl/api/authentication/validate" `
        -Headers (New-BasicAuthHeader -UserName "admin" -Password $sonarPassword) `
        -TimeoutSec 30
    if (-not $sonarValidation.valid) {
        throw "SonarQube admin credentials were not accepted."
    }
    Write-Host "SonarQube login ready: admin / $sonarPassword" -ForegroundColor Green
}

if (-not $SkipArgoCd) {
    Write-Host "Setting up Argo CD demo admin password..." -ForegroundColor Cyan
    Set-ArgoCdAdminPassword -Password $ArgoCdPassword
    Write-Host "Argo CD login ready: admin / $ArgoCdPassword" -ForegroundColor Green
}

if (-not $SkipGrafana) {
    Write-Host "Setting up Grafana demo admin password..." -ForegroundColor Cyan
    Set-GrafanaAdminPassword -UserName $grafanaUser -Password $GrafanaPassword
    Write-Host "Grafana login ready: $grafanaUser / $GrafanaPassword" -ForegroundColor Green
}

Write-Host ""
Write-Host "Local demo accounts are ready." -ForegroundColor Green
