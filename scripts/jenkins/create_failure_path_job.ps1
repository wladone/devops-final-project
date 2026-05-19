param (
    [string]$BaseUrl = "http://localhost:8080",
    [string]$JobName = "data-quality-monitor-failure-paths"
)

$ErrorActionPreference = "Stop"

# Reuse the project-job creator with a custom Jenkinsfile path. The job is
# parameterised only with PROJECT_DIR; everything else is hardcoded so a
# scheduled cron run does not need any operator input.
& (Join-Path $PSScriptRoot "create_job.ps1") `
    -JobName $JobName `
    -BaseUrl $BaseUrl `
    -PipelineFilePath "jenkins/Jenkinsfile.failure-paths" `
    -Description "Nightly negative-path smoke: verifies each CI gate fails fast on bad input."
