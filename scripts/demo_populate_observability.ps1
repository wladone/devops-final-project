param (
    [string]$Namespace = "dq-monitor-dev",
    [int]$Runs = 5,
    [int]$DelaySeconds = 5,
    [int]$TimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$grafanaDashboardUrl = "http://localhost:3000/d/dq-observability-demo/data-quality-monitoring-operations"
$prometheusTargetsUrl = "http://localhost:9090/targets"
$prometheusJobsQueryUrl = "http://localhost:9090/query?g0.expr=sum(increase(kube_job_status_succeeded%7Bnamespace%3D%22dq-monitor-dev%22%7D%5B6h%5D))&g0.tab=table&g0.range_input=1h"

function Get-RunnerCronJobName {
    param ([string]$TargetNamespace)

    $cronJobs = kubectl get cronjob -n $TargetNamespace -o jsonpath="{range .items[*]}{.metadata.name}{'\n'}{end}"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not list CronJobs in namespace '$TargetNamespace'."
    }

    $runner = $cronJobs -split "`n" |
        Where-Object { $_ -match "data-quality-monitor" -and $_ -match "runner" } |
        Select-Object -First 1

    if (-not $runner) {
        throw "No data-quality runner CronJob was found in namespace '$TargetNamespace'."
    }

    return $runner.Trim()
}

function Wait-ForJobFinished {
    param (
        [string]$TargetNamespace,
        [string]$JobName,
        [int]$WaitSeconds
    )

    $deadline = (Get-Date).AddSeconds($WaitSeconds)
    do {
        $status = kubectl get job $JobName -n $TargetNamespace -o jsonpath="{.status.succeeded}:{.status.failed}" 2>$null
        if ($LASTEXITCODE -eq 0) {
            if ($status -match "^1:") {
                return "Succeeded"
            }
            if ($status -match ":1$") {
                return "Failed"
            }
        }

        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $deadline)

    return "TimedOut"
}

Push-Location $repoRoot
try {
    Write-Host "Finding Kubernetes data-quality runner CronJob..." -ForegroundColor Cyan
    $cronJobName = Get-RunnerCronJobName -TargetNamespace $Namespace
    Write-Host "Using CronJob: $cronJobName" -ForegroundColor White

    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $summary = @()

    for ($index = 1; $index -le $Runs; $index++) {
        $jobName = "dq-observe-$timestamp-$index"
        Write-Host "Creating load job $jobName from $cronJobName..." -ForegroundColor Cyan
        kubectl create job $jobName -n $Namespace --from="cronjob/$cronJobName" | Out-Null

        $status = Wait-ForJobFinished -TargetNamespace $Namespace -JobName $jobName -WaitSeconds $TimeoutSeconds
        $summary += [pscustomobject]@{
            job = $jobName
            status = $status
        }

        Write-Host "$jobName -> $status" -ForegroundColor White
        if ($index -lt $Runs) {
            Start-Sleep -Seconds $DelaySeconds
        }
    }

    Write-Host ""
    Write-Host "Observability population complete." -ForegroundColor Green
    $summary | Format-Table -AutoSize
    Write-Host ""
    Write-Host "Open Grafana: $grafanaDashboardUrl" -ForegroundColor Yellow
    Write-Host "Open Prometheus targets: $prometheusTargetsUrl" -ForegroundColor Yellow
    Write-Host "Open Prometheus job query: $prometheusJobsQueryUrl" -ForegroundColor Yellow
}
finally {
    Pop-Location
}
