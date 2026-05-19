param (
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$jenkinsJobUrl = "http://localhost:8080/job/data-quality-monitor-local/"
$jenkinsBuildUrl = "http://localhost:8080/job/data-quality-monitor-local/lastBuild/"
$argocdUrl = "https://127.0.0.1:28080"
$dashboardUrl = "http://127.0.0.1:28501"

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

Push-Location $repoRoot
try {
    . (Join-Path $repoRoot "scripts\jenkins\common.ps1")
    $jenkinsSettings = Get-JenkinsSettings
    $jenkinsUser = $jenkinsSettings["JENKINS_ADMIN_ID"]
    $jenkinsPassword = $jenkinsSettings["JENKINS_ADMIN_PASSWORD"]

    Write-Host "Starting local GitOps support..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\gitops\start.ps1")

    Write-Host "Starting Jenkins..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\jenkins\start.ps1")
    if (-not (Wait-ForJenkinsApi -BaseUrl "http://localhost:8080" -UserName $jenkinsUser -Password $jenkinsPassword -TimeoutSeconds 240)) {
        throw "Jenkins did not become ready for authenticated API calls in time."
    }

    Write-Host "Running the light Jenkins demo..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\jenkins\run_gitops_demo.ps1") -RefreshJob:$true

    Write-Host "Starting local browser access..." -ForegroundColor Cyan
    Ensure-PortForwardReady -Port 28080 -ScriptPath (Join-Path $repoRoot "scripts\gitops\port_forward_argocd.ps1") -Url $argocdUrl -TimeoutSeconds 120 -SkipTlsCheck $true -Name "Argo CD"
    Ensure-PortForwardReady -Port 28501 -ScriptPath (Join-Path $repoRoot "scripts\gitops\port_forward_dashboard.ps1") -Url $dashboardUrl -TimeoutSeconds 120 -Name "Dashboard"

    $argocdPassword = ""
    try {
        $secretValue = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
        if ($secretValue) {
            $argocdPassword = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($secretValue))
        }
    }
    catch {
        $argocdPassword = ""
    }

    Write-Host ""
    Write-Host "Demo light is ready." -ForegroundColor Green
    Write-Host ""
    Write-Host "Open these pages:" -ForegroundColor Yellow
    Write-Host "Jenkins Stage View: $jenkinsJobUrl" -ForegroundColor White
    Write-Host "Jenkins Latest Build: $jenkinsBuildUrl" -ForegroundColor White
    Write-Host "Argo CD: $argocdUrl" -ForegroundColor White
    Write-Host "Dashboard: $dashboardUrl" -ForegroundColor White
    Write-Host ""
    Write-Host "Logins:" -ForegroundColor Yellow
    Write-Host "Jenkins: $jenkinsUser / $jenkinsPassword" -ForegroundColor White
    if ($argocdPassword) {
        Write-Host "Argo CD: admin / $argocdPassword" -ForegroundColor White
    }
    else {
        Write-Host "Argo CD: admin / <check argocd-initial-admin-secret>" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "Stop later with:" -ForegroundColor Yellow
    Write-Host "powershell -ExecutionPolicy Bypass -File scripts/jenkins/stop.ps1" -ForegroundColor White
    Write-Host "powershell -ExecutionPolicy Bypass -File scripts/gitops/stop.ps1" -ForegroundColor White

    if ($OpenBrowser) {
        Start-Process $jenkinsBuildUrl
        Start-Process $argocdUrl
        Start-Process $dashboardUrl
    }
}
finally {
    Pop-Location
}
