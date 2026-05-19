param (
    [string]$JobName = "data-quality-monitor-local",
    [string]$BaseUrl = "http://localhost:8080"
)

$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "..\jenkins\build_job.ps1"

& $script `
    -JobName $JobName `
    -BaseUrl $BaseUrl `
    -ProjectDir "/workspace/data-quality-monitor" `
    -InputFile "data/raw/psq_customer_base_v8_stress.csv" `
    -RulesFile "config/rules.yml" `
    -OutputDir "reports/ci" `
    -SkipCheckout:$true `
    -RunHelmValidation:$true `
    -HelmValuesFile "helm/data-quality-monitor/values-dev.yaml" `
    -RunTerraformValidate:$true `
    -RunSecurityScan:$true `
    -RegistryImage "localhost:5001/data-quality-monitor" `
    -RunDeploy:$true `
    -InventoryPath "lab/ansible/inventory.ini" `
    -AnsibleExtraVars "dashboard_port=18501 dashboard_healthcheck_url=http://host.docker.internal:18501" `
    -DashboardUrl "http://host.docker.internal:18501" `
    -WaitForCompletion:$true
