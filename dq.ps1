# dq.ps1 -- single entrypoint for the Data Quality Monitor demo stack.
#
# Goals:
#   * One command brings the platform up, one tears it down, one tests it.
#   * Wraps the existing scripts under scripts/ so this stays a thin router.
#   * Always emits UTF-8 logs (the underlying PowerShell scripts default to UTF-16
#     which makes grep/tail painful on Windows).
#
# Typical use:
#   dq up               # full stack
#   dq up -light        # Jenkins + SonarQube only
#   dq build -strict    # Jenkins full job with Sonar + Trivy gates enforcing
#   dq status           # one screen of platform state
#   dq test             # pytest, no Docker required
#   dq down             # tear down lab + kind + Jenkins/Sonar
[CmdletBinding(PositionalBinding = $false)]
param (
    [Parameter(Position = 0)]
    [ValidateSet("up", "down", "status", "build", "test", "logs", "")]
    [string]$Command = "",

    [switch]$Light,
    [switch]$Strict,
    [switch]$Deploy,
    [string]$Service = "",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Extra
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

function Show-Usage {
    Write-Host ""
    Write-Host "Data Quality Monitor -- dq.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Yellow
    Write-Host "  dq up [-light]          Bring the platform up. -light = Jenkins + SonarQube only." -ForegroundColor White
    Write-Host "  dq down                 Tear everything down." -ForegroundColor White
    Write-Host "  dq status               One screen: Docker, Jenkins jobs, lab, kind." -ForegroundColor White
    Write-Host "  dq build [-strict]      Trigger the Jenkins full job. -strict enables Sonar + Trivy gates." -ForegroundColor White
    Write-Host "  dq test                 Run pytest locally (no Docker required)." -ForegroundColor White
    Write-Host "  dq logs -service NAME   Tail logs from jenkins | sonarqube | argocd | grafana | prometheus." -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\dq.ps1 up" -ForegroundColor Gray
    Write-Host "  .\dq.ps1 build -strict" -ForegroundColor Gray
    Write-Host "  .\dq.ps1 logs -service jenkins" -ForegroundColor Gray
    Write-Host ""
}

function Test-DockerReady {
    try {
        $null = docker info 2>$null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Start-DockerDesktop {
    $dockerExe = Join-Path ${env:ProgramFiles} "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $dockerExe)) {
        Write-Host "Docker Desktop not found at $dockerExe -- start it manually." -ForegroundColor Red
        return $false
    }

    Write-Host "Starting Docker Desktop and waiting for the daemon..." -ForegroundColor Cyan
    Start-Process -FilePath $dockerExe -WindowStyle Hidden
    $deadline = (Get-Date).AddMinutes(3)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerReady) {
            Write-Host "Docker is ready." -ForegroundColor Green
            return $true
        }
        Start-Sleep -Seconds 5
    }
    Write-Host "Docker daemon did not respond within 3 minutes." -ForegroundColor Red
    return $false
}

function Invoke-Up {
    if (-not (Test-DockerReady)) {
        if (-not (Start-DockerDesktop)) { exit 1 }
    }

    $script = if ($Light) { "scripts\demo_light.ps1" } else { "scripts\demo_full.ps1" }
    $absScript = Join-Path $repoRoot $script
    Write-Host "Running $script..." -ForegroundColor Cyan
    & $absScript
}

function Invoke-Down {
    Write-Host "Tearing down the lab (Terraform)..." -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\lab\stop.ps1")

    $gitopsStop = Join-Path $repoRoot "scripts\gitops\stop.ps1"
    if (Test-Path $gitopsStop) {
        Write-Host "Tearing down the GitOps stack (kind + Argo)..." -ForegroundColor Cyan
        & $gitopsStop
    }

    $jenkinsStop = Join-Path $repoRoot "scripts\jenkins\stop.ps1"
    if (Test-Path $jenkinsStop) {
        Write-Host "Stopping Jenkins + SonarQube..." -ForegroundColor Cyan
        & $jenkinsStop
    }

    Write-Host "All stacks stopped." -ForegroundColor Green
}

function Invoke-Status {
    Write-Host ""
    Write-Host "== Docker ==" -ForegroundColor Yellow
    if (Test-DockerReady) {
        Write-Host "  daemon: ok" -ForegroundColor Green
    } else {
        Write-Host "  daemon: not running" -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host "== Containers (project-tagged) ==" -ForegroundColor Yellow
    docker ps --filter "name=dq-" --filter "name=data-quality-" --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"

    Write-Host ""
    Write-Host "== Jenkins jobs ==" -ForegroundColor Yellow
    $auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin123!"))
    $h = @{Authorization = "Basic $auth"}
    foreach ($job in 'data-quality-monitor-demo-e2e','data-quality-monitor-full','data-quality-monitor-delivery','data-quality-monitor-failure-paths') {
        try {
            $r = Invoke-RestMethod -Uri "http://localhost:8080/job/$job/api/json?tree=lastBuild[number,result,building]" -Headers $h -TimeoutSec 5 -ErrorAction Stop
            $building = if ($r.lastBuild.building) { " (building)" } else { "" }
            $color = if ($r.lastBuild.result -eq 'SUCCESS') { 'Green' } elseif ($r.lastBuild.result -eq 'FAILURE') { 'Red' } else { 'Yellow' }
            Write-Host ("  {0,-40} #{1,-4} {2}{3}" -f $job, $r.lastBuild.number, $r.lastBuild.result, $building) -ForegroundColor $color
        }
        catch {
            Write-Host ("  {0,-40} unreachable" -f $job) -ForegroundColor DarkGray
        }
    }

    Write-Host ""
    Write-Host "== kind cluster ==" -ForegroundColor Yellow
    try {
        kubectl get nodes 2>$null | Select-Object -First 5
    }
    catch {
        Write-Host "  kubectl not available or cluster not running" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "Dashboards:" -ForegroundColor Yellow
    Write-Host "  Jenkins         http://localhost:8080" -ForegroundColor White
    Write-Host "  SonarQube       http://localhost:9000" -ForegroundColor White
    Write-Host "  Argo CD         https://127.0.0.1:28080" -ForegroundColor White
    Write-Host "  Grafana         http://localhost:3000" -ForegroundColor White
    Write-Host "  Classic app     http://localhost:18501" -ForegroundColor White
    Write-Host "  Kubernetes app  http://127.0.0.1:28501" -ForegroundColor White
}

function Invoke-Build {
    $buildArgs = @{
        JobName                 = "data-quality-monitor-full"
        ProjectDir              = "/workspace/data-quality-monitor"
        RunSonarScan            = [bool]$Strict
        SonarHostUrl            = "http://sonarqube:9000"
        SonarTokenCredentialsId = "sonar-local-token"
        RunSecurityScan         = [bool]$Strict
        RegistryImage           = "localhost:5001/data-quality-monitor"
        RunHelmValidation       = $true
        HelmValuesFile          = "helm/data-quality-monitor/values-kind-full.yaml"
        RunDockerPublish        = $true
        RunDeploy               = [bool]$Deploy
        WaitForCompletion       = $true
        TimeoutSeconds          = 900
        AcceptedResults         = @("SUCCESS", "FAILURE", "UNSTABLE")
        PassThru                = $true
    }

    $label = if ($Strict) { "strict (Sonar + Trivy enforcing)" } else { "default" }
    Write-Host "Triggering Jenkins build -- $label" -ForegroundColor Cyan
    & (Join-Path $repoRoot "scripts\jenkins\build_job.ps1") @buildArgs
}

function Invoke-Test {
    Write-Host "Running pytest..." -ForegroundColor Cyan
    Push-Location $repoRoot
    try {
        python -m pytest
    }
    finally {
        Pop-Location
    }
}

function Invoke-Logs {
    if (-not $Service) {
        Write-Host "Specify -service: jenkins | sonarqube | argocd | grafana | prometheus" -ForegroundColor Red
        return
    }
    $containerMap = @{
        jenkins    = "data-quality-jenkins"
        sonarqube  = "data-quality-sonarqube"
        grafana    = "dq-grafana"
        prometheus = "dq-prometheus"
    }
    if ($containerMap.ContainsKey($Service)) {
        docker logs --tail 200 -f $containerMap[$Service]
        return
    }
    if ($Service -eq "argocd") {
        kubectl -n argocd logs deploy/argocd-server --tail 200 -f
        return
    }
    Write-Host "Unknown service: $Service" -ForegroundColor Red
}

switch ($Command) {
    "up"     { Invoke-Up }
    "down"   { Invoke-Down }
    "status" { Invoke-Status }
    "build"  { Invoke-Build }
    "test"   { Invoke-Test }
    "logs"   { Invoke-Logs }
    default  { Show-Usage }
}
