param (
    [string]$BaseUrl = "http://localhost:8080"
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "create_job.ps1") -JobName "data-quality-monitor-full" -BaseUrl $BaseUrl
& (Join-Path $PSScriptRoot "create_job.ps1") -JobName "data-quality-monitor-delivery" -BaseUrl $BaseUrl
& (Join-Path $PSScriptRoot "create_job.ps1") -JobName "data-quality-monitor-demo-e2e" -BaseUrl $BaseUrl -JobType "orchestrator"

Write-Host "Full demo jobs are ready in Jenkins." -ForegroundColor Green
