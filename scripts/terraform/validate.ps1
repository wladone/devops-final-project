param (
    [string]$TerraformEnvironments = "dev staging prod"
)

$ErrorActionPreference = "Stop"
$jenkinsContainer = "data-quality-jenkins"
$command = "cd /workspace/data-quality-monitor && chmod +x scripts/ci/run_terraform_validate.sh && ./scripts/ci/run_terraform_validate.sh '$TerraformEnvironments'"

docker exec $jenkinsContainer sh -lc $command
