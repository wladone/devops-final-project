param (
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$jenkinsBaseUrl = "http://localhost:8080"
$jenkinsOrchestratorJobUrl = "$jenkinsBaseUrl/job/data-quality-monitor-demo-e2e/"
$jenkinsFullJobUrl = "$jenkinsBaseUrl/job/data-quality-monitor-full/"
$jenkinsDeliveryJobUrl = "$jenkinsBaseUrl/job/data-quality-monitor-delivery/"
$sonarUrl = "http://localhost:9000"
$argocdUrl = "https://127.0.0.1:28080"
$grafanaUrl = "http://localhost:3000"
$grafanaDataQualityUrl = "http://localhost:3000/d/dq-observability-demo/data-quality-monitoring-operations"
$prometheusUrl = "http://localhost:9090"
$prometheusTargetsUrl = "http://localhost:9090/targets"
$prometheusQuickQueryUrl = "http://localhost:9090/query?g0.expr=sum(up)&g0.tab=table&g0.range_input=1h"
$classicDashboardUrl = "http://localhost:18501"
$k8sDashboardUrl = "http://127.0.0.1:28501"

function Test-LocalPort {
    param (
        [int]$Port
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(1000, $false)) {
            return $false
        }

        $client.EndConnect($async) | Out-Null
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Wait-ForHttp {
    param (
        [string]$Url,
        [int]$TimeoutSeconds = 60,
        [switch]$SkipTlsCheck
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $args = @("-I", "--max-time", "5")
        if ($SkipTlsCheck) {
            $args += "-k"
        }
        $args += $Url

        & curl.exe @args | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }

        $getArgs = @("-fsS", "--max-time", "5", "-o", "NUL")
        if ($SkipTlsCheck) {
            $getArgs += "-k"
        }
        $getArgs += $Url

        & curl.exe @getArgs | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return $true
        }

        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    return $false
}

function Wait-ForJenkinsApi {
    param (
        [string]$BaseUrl,
        [string]$UserName,
        [string]$Password,
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $authHeaders = Get-JenkinsAuthHeader -UserName $UserName -Password $Password
            $null = Get-JenkinsWebSessionContext -BaseUrl $BaseUrl -AuthHeaders $authHeaders
            return $true
        }
        catch {
            Start-Sleep -Seconds 3
        }
    } while ((Get-Date) -lt $deadline)

    return $false
}

function Assert-HttpAvailable {
    param (
        [string]$Url,
        [int]$TimeoutSeconds = 60,
        [bool]$SkipTlsCheck = $false,
        [string]$Name = "endpoint"
    )

    if (-not (Wait-ForHttp -Url $Url -TimeoutSeconds $TimeoutSeconds -SkipTlsCheck:$SkipTlsCheck)) {
        throw "$Name did not become reachable at $Url in time."
    }
}

function Stop-LocalPortOwner {
    param (
        [int]$Port
    )

    try {
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique |
            Where-Object { $_ } |
            ForEach-Object {
                Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
            }
    }
    catch {
        Write-Warning "Could not stop existing listener on port ${Port}: $($_.Exception.Message)"
    }
}

function Ensure-PortForwardReady {
    param (
        [int]$Port,
        [string]$ScriptPath,
        [string]$Url,
        [int]$TimeoutSeconds = 120,
        [bool]$SkipTlsCheck = $false,
        [string]$Name = "port-forwarded endpoint"
    )

    for ($attempt = 1; $attempt -le 3; $attempt++) {
        if (Wait-ForHttp -Url $Url -TimeoutSeconds 5 -SkipTlsCheck:$SkipTlsCheck) {
            return
        }

        Stop-LocalPortOwner -Port $Port
        Start-Process powershell -WindowStyle Hidden -ArgumentList "-ExecutionPolicy Bypass -File `"$ScriptPath`""
        Start-Sleep -Seconds 2

        if (Wait-ForHttp -Url $Url -TimeoutSeconds $TimeoutSeconds -SkipTlsCheck:$SkipTlsCheck) {
            return
        }
    }

    throw "$Name did not become reachable at $Url after starting the port-forward."
}

function Clear-LocalDemoTempArtifacts {
    param (
        [string]$RootPath
    )

    $tmpPath = Join-Path $RootPath ".tmp"
    if (-not (Test-Path $tmpPath)) {
        return
    }

    Get-ChildItem -Path $tmpPath -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "pip-*" -or $_.Name -like "tmp*" } |
        ForEach-Object {
            $artifactPath = $_.FullName
            try {
                $_.Attributes = [System.IO.FileAttributes]::Normal
                Remove-Item -LiteralPath $artifactPath -Recurse -Force -ErrorAction Stop
            }
            catch {
                Write-Warning "Could not remove temporary artifact '$artifactPath': $($_.Exception.Message)"
            }
        }
}

Push-Location $repoRoot
try {
    . (Join-Path $repoRoot "scripts\jenkins\common.ps1")
    $settings = Get-JenkinsSettings
    $jenkinsUser = $settings["JENKINS_ADMIN_ID"]
    $jenkinsPassword = $settings["JENKINS_ADMIN_PASSWORD"]
    $sonarAdminPassword = if ($settings.ContainsKey("SONARQUBE_ADMIN_PASSWORD") -and $settings["SONARQUBE_ADMIN_PASSWORD"]) {
        $settings["SONARQUBE_ADMIN_PASSWORD"]
    } else {
        "admin123!"
    }
    $grafanaAdminUser = if ($settings.ContainsKey("GRAFANA_ADMIN_USER") -and $settings["GRAFANA_ADMIN_USER"]) {
        $settings["GRAFANA_ADMIN_USER"]
    } else {
        "admin"
    }
    $grafanaAdminPassword = if ($settings.ContainsKey("GRAFANA_ADMIN_PASSWORD") -and $settings["GRAFANA_ADMIN_PASSWORD"]) {
        $settings["GRAFANA_ADMIN_PASSWORD"]
    } else {
        "admin123!"
    }
    $argocdAdminPassword = if ($settings.ContainsKey("ARGOCD_ADMIN_PASSWORD") -and $settings["ARGOCD_ADMIN_PASSWORD"]) {
        $settings["ARGOCD_ADMIN_PASSWORD"]
    } else {
        "admin123!"
    }

    Write-Host "Cleaning stale local demo temp artifacts..." -ForegroundColor Cyan
    Clear-LocalDemoTempArtifacts -RootPath $repoRoot

    Write-Host "Starting the local registry and Linux target..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\lab\start.ps1")

    Write-Host "Ensuring the local kind cluster exists..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\kind\create_cluster.ps1")

    Write-Host "Starting the local GitOps git daemon..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\gitops\start.ps1")

    $argocdInstalled = $false
    try {
        kubectl get deployment argocd-server -n argocd | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $argocdInstalled = $true
        }
    }
    catch {
        $argocdInstalled = $false
    }

    if (-not $argocdInstalled) {
        Write-Host "Installing Argo CD into the local cluster..." -ForegroundColor Cyan
        & (Join-Path $repoRoot "scripts\gitops\install_argocd.ps1")
    }

    Write-Host "Bootstrapping monitoring in kind..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\gitops\bootstrap_monitoring.ps1")

    Write-Host "Ensuring the Argo CD application exists..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\gitops\bootstrap_app.ps1") -AppManifest "argocd\app-kind-full.yaml"

    Write-Host "Starting Jenkins and SonarQube..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\jenkins\start.ps1")
    if (-not (Wait-ForJenkinsApi -BaseUrl $jenkinsBaseUrl -UserName $jenkinsUser -Password $jenkinsPassword -TimeoutSeconds 240)) {
        throw "Jenkins did not become ready for authenticated API calls in time."
    }

    Write-Host "Setting up local demo accounts..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\setup_demo_accounts.ps1") -JenkinsBaseUrl $jenkinsBaseUrl -SonarUrl $sonarUrl

    Write-Host "Creating the full Jenkins jobs..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\jenkins\create_full_jobs.ps1") -BaseUrl $jenkinsBaseUrl

    Write-Host "Preparing the GitOps source clone for delivery..." -ForegroundColor Cyan
    $preparedSource = & (Join-Path $repoRoot "scripts\jenkins\prepare_gitops_source.ps1")

    Assert-HttpAvailable -Url $sonarUrl -TimeoutSeconds 120 -Name "SonarQube"
    Assert-HttpAvailable -Url $classicDashboardUrl -TimeoutSeconds 120 -Name "Classic dashboard"

    Ensure-PortForwardReady -Port 28080 -ScriptPath (Join-Path $repoRoot "scripts\gitops\port_forward_argocd.ps1") -Url $argocdUrl -TimeoutSeconds 120 -SkipTlsCheck $true -Name "Argo CD"
    Ensure-PortForwardReady -Port 28501 -ScriptPath (Join-Path $repoRoot "scripts\gitops\port_forward_dashboard.ps1") -Url $k8sDashboardUrl -TimeoutSeconds 120 -Name "Kubernetes dashboard"
    Ensure-PortForwardReady -Port 3000 -ScriptPath (Join-Path $repoRoot "scripts\gitops\port_forward_grafana.ps1") -Url $grafanaUrl -TimeoutSeconds 120 -Name "Grafana"
    Ensure-PortForwardReady -Port 9090 -ScriptPath (Join-Path $repoRoot "scripts\gitops\port_forward_prometheus.ps1") -Url $prometheusUrl -TimeoutSeconds 120 -Name "Prometheus"

    Write-Host "Running the demo orchestrator job..." -ForegroundColor Cyan
    $orchestratorBuild = & (Join-Path $repoRoot "scripts\jenkins\build_job.ps1") `
        -JobName "data-quality-monitor-demo-e2e" `
        -BaseUrl $jenkinsBaseUrl `
        -IncludeProjectParameters $false `
        -WaitForCompletion $true `
        -PassThru `
        -AdditionalParameters @{
            FULL_PROJECT_DIR = "/workspace/data-quality-monitor"
            DELIVERY_PROJECT_DIR = $preparedSource.ContainerProjectDir
            REGISTRY_IMAGE = "localhost:5001/data-quality-monitor"
            SONAR_PROJECT_KEY = "data-quality-monitor"
            SONAR_TOKEN_CREDENTIALS_ID = "sonar-local-token"
            ARGOCD_APP_NAME = "data-quality-monitor-kind"
            ARGOCD_NAMESPACE = "argocd"
            K8S_NAMESPACE = "dq-monitor-dev"
            K8S_RUNNER_CRONJOB = "data-quality-monitor-data-quality-monitor-runner"
            K8S_DASHBOARD_RESOURCE = "svc/data-quality-monitor-data-quality-monitor-dashboard"
            PUBLIC_JENKINS_BASE_URL = $jenkinsBaseUrl
            PUBLIC_SONAR_URL = $sonarUrl
            PUBLIC_ARGOCD_URL = $argocdUrl
            PUBLIC_GRAFANA_URL = $grafanaUrl
            PUBLIC_PROMETHEUS_URL = $prometheusUrl
            PUBLIC_CLASSIC_DASHBOARD_URL = $classicDashboardUrl
            PUBLIC_K8S_DASHBOARD_URL = $k8sDashboardUrl
            INTERNAL_REGISTRY_BASE_URL = "http://host.docker.internal:5001"
            INTERNAL_SONAR_URL = "http://sonarqube:9000"
            INTERNAL_CLASSIC_DASHBOARD_URL = "http://host.docker.internal:18501"
            INTERNAL_K8S_DASHBOARD_URL = "http://host.docker.internal:28501"
            INTERNAL_GRAFANA_URL = "http://host.docker.internal:3000"
            INTERNAL_PROMETHEUS_READY_URL = "http://host.docker.internal:9090/-/ready"
        }

    Write-Host "Refreshing local UI port-forwards after deployment..." -ForegroundColor Cyan
    Ensure-PortForwardReady -Port 28080 -ScriptPath (Join-Path $repoRoot "scripts\gitops\port_forward_argocd.ps1") -Url $argocdUrl -TimeoutSeconds 120 -SkipTlsCheck $true -Name "Argo CD"
    Ensure-PortForwardReady -Port 28501 -ScriptPath (Join-Path $repoRoot "scripts\gitops\port_forward_dashboard.ps1") -Url $k8sDashboardUrl -TimeoutSeconds 120 -Name "Kubernetes dashboard"
    Ensure-PortForwardReady -Port 3000 -ScriptPath (Join-Path $repoRoot "scripts\gitops\port_forward_grafana.ps1") -Url $grafanaUrl -TimeoutSeconds 120 -Name "Grafana"
    Ensure-PortForwardReady -Port 9090 -ScriptPath (Join-Path $repoRoot "scripts\gitops\port_forward_prometheus.ps1") -Url $prometheusUrl -TimeoutSeconds 120 -Name "Prometheus"

    Write-Host ""
    Write-Host "Demo full is ready." -ForegroundColor Green
    Write-Host ""
    Write-Host "Build summary:" -ForegroundColor Yellow
    Write-Host ("Orchestrator job: #{0} ({1})" -f $orchestratorBuild.BuildNumber, $orchestratorBuild.Result) -ForegroundColor White
    Write-Host ""
    Write-Host "Open these pages:" -ForegroundColor Yellow
    Write-Host "Jenkins orchestrator: $($orchestratorBuild.Url)" -ForegroundColor White
    Write-Host "Jenkins demo links artifact: $($orchestratorBuild.Url)artifact/demo-links.md" -ForegroundColor White
    Write-Host "Jenkins full job: $jenkinsFullJobUrl" -ForegroundColor White
    Write-Host "Jenkins delivery job: $jenkinsDeliveryJobUrl" -ForegroundColor White
    Write-Host "SonarQube: $sonarUrl" -ForegroundColor White
    Write-Host "Argo CD: $argocdUrl" -ForegroundColor White
    Write-Host "Grafana home: $grafanaUrl" -ForegroundColor White
    Write-Host "Grafana Operations dashboard: $grafanaDataQualityUrl" -ForegroundColor White
    Write-Host "Prometheus home: $prometheusUrl" -ForegroundColor White
    Write-Host "Prometheus targets: $prometheusTargetsUrl" -ForegroundColor White
    Write-Host "Prometheus quick query: $prometheusQuickQueryUrl" -ForegroundColor White
    Write-Host "Classic dashboard: $classicDashboardUrl" -ForegroundColor White
    Write-Host "Kubernetes dashboard: $k8sDashboardUrl" -ForegroundColor White
    Write-Host ""
    Write-Host "Logins:" -ForegroundColor Yellow
    Write-Host "Jenkins: $jenkinsUser / $jenkinsPassword" -ForegroundColor White
    Write-Host "SonarQube: admin / $sonarAdminPassword" -ForegroundColor White
    Write-Host "Grafana: $grafanaAdminUser / $grafanaAdminPassword" -ForegroundColor White
    Write-Host "Argo CD: admin / $argocdAdminPassword" -ForegroundColor White

    if ($OpenBrowser) {
        Start-Process $($orchestratorBuild.Url)
        Start-Process $jenkinsFullJobUrl
        Start-Process $jenkinsDeliveryJobUrl
        Start-Process $sonarUrl
        Start-Process $argocdUrl
        Start-Process $grafanaUrl
        Start-Process $prometheusUrl
        Start-Process $classicDashboardUrl
        Start-Process $k8sDashboardUrl
    }
}
finally {
    Pop-Location
}
