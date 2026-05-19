param (
    [string]$JobName = "data-quality-monitor-local",
    [string]$BaseUrl = "http://localhost:8080",
    [string]$ProjectDir = "/workspace/data-quality-monitor",
    [string]$InputFile = "data/raw/psq_customer_base_v8_stress.csv",
    [string]$RulesFile = "config/rules.yml",
    [string]$OutputDir = "reports/ci",
    [bool]$SkipCheckout = $true,
    [bool]$RunUnitTests = $true,
    [bool]$RunSonarScan = $false,
    [string]$SonarHostUrl = "",
    [string]$SonarTokenCredentialsId = "",
    [bool]$RunDataQualityJob = $true,
    [bool]$RunHelmValidation = $false,
    [string]$HelmValuesFile = "helm/data-quality-monitor/values-dev.yaml",
    [string]$HelmReleaseName = "data-quality-monitor",
    [string]$HelmNamespace = "dq-monitor-dev",
    [string]$K8sNamespace = "dq-monitor-dev",
    [string]$K8sRunnerCronJob = "data-quality-monitor-data-quality-monitor-runner",
    [string]$K8sDashboardResource = "svc/data-quality-monitor-data-quality-monitor-dashboard",
    [bool]$RunTerraformValidate = $false,
    [string]$TerraformEnvironments = "dev staging prod",
    [string]$ImageTagOverride = "",
    [bool]$RunDockerBuild = $true,
    [bool]$RunSecurityScan = $false,
    [bool]$RunDockerPublish = $true,
    [bool]$RunDeploy = $false,
    [string]$InventoryPath = "ansible/inventory.ini",
    [string]$AnsibleExtraVars = "",
    [string]$RegistryImage = "",
    [bool]$RunGitOpsUpdate = $false,
    [string]$GitOpsValuesFile = "helm/data-quality-monitor/values-kind-local.yaml",
    [string]$GitOpsTargetBranch = "main",
    [string]$GitOpsPushRemote = "origin",
    [string]$GitUserName = "jenkins-bot",
    [string]$GitUserEmail = "jenkins@example.local",
    [bool]$RunArgoCdSync = $false,
    [string]$ArgoCdAppName = "data-quality-monitor-kind",
    [string]$ArgoCdSyncMode = "server",
    [string]$ArgoCdNamespace = "argocd",
    [string]$ArgoCdServer = "",
    [string]$DashboardUrl = "",
    [string]$K8sDashboardUrl = "",
    [bool]$IncludeProjectParameters = $true,
    [hashtable]$AdditionalParameters = @{},
    [bool]$WaitForCompletion = $false,
    [int]$TimeoutSeconds = 900,
    [string[]]$AcceptedResults = @("SUCCESS"),
    [switch]$PassThru
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

$settings = Get-JenkinsSettings
$userName = $settings["JENKINS_ADMIN_ID"]
$password = $settings["JENKINS_ADMIN_PASSWORD"]
$authHeaders = Get-JenkinsAuthHeader -UserName $userName -Password $password
$webContext = Get-JenkinsWebSessionContext -BaseUrl $BaseUrl -AuthHeaders $authHeaders
$headers = $webContext.Headers
$webSession = $webContext.WebSession
$encodedJobName = [uri]::EscapeDataString($JobName)

$parameterDeadline = (Get-Date).AddSeconds(60)
do {
    $parameterInfo = Invoke-RestMethod -Uri "$BaseUrl/job/$encodedJobName/api/json?tree=property[parameterDefinitions[name]],nextBuildNumber" -Headers $authHeaders -WebSession $webSession
    $parameterDefinitions = @()
    foreach ($property in @($parameterInfo.property)) {
        if ($property.parameterDefinitions) {
            $parameterDefinitions += @($property.parameterDefinitions)
        }
    }

    if ($parameterDefinitions.Count -gt 0) {
        $jobInfo = $parameterInfo
        break
    }

    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $parameterDeadline)

if (-not $jobInfo) {
    throw "Jenkins job '$JobName' does not expose parameter definitions yet. Recreate the job before triggering it."
}

$targetBuildNumber = [int]$jobInfo.nextBuildNumber

$body = @{}

if ($IncludeProjectParameters) {
    $body = @{
        PROJECT_DIR = $ProjectDir
        INPUT_FILE = $InputFile
        RULES_FILE = $RulesFile
        OUTPUT_DIR = $OutputDir
        RUN_UNIT_TESTS = $RunUnitTests.ToString().ToLowerInvariant()
        RUN_SONAR_SCAN = $RunSonarScan.ToString().ToLowerInvariant()
        SONAR_HOST_URL = $SonarHostUrl
        SONAR_TOKEN_CREDENTIALS_ID = $SonarTokenCredentialsId
        RUN_DATA_QUALITY_JOB = $RunDataQualityJob.ToString().ToLowerInvariant()
        RUN_HELM_VALIDATION = $RunHelmValidation.ToString().ToLowerInvariant()
        HELM_VALUES_FILE = $HelmValuesFile
        HELM_RELEASE_NAME = $HelmReleaseName
        HELM_NAMESPACE = $HelmNamespace
        K8S_NAMESPACE = $K8sNamespace
        K8S_RUNNER_CRONJOB = $K8sRunnerCronJob
        K8S_DASHBOARD_RESOURCE = $K8sDashboardResource
        RUN_TERRAFORM_VALIDATE = $RunTerraformValidate.ToString().ToLowerInvariant()
        TERRAFORM_ENVIRONMENTS = $TerraformEnvironments
        IMAGE_TAG_OVERRIDE = $ImageTagOverride
        RUN_DOCKER_BUILD = $RunDockerBuild.ToString().ToLowerInvariant()
        RUN_SECURITY_SCAN = $RunSecurityScan.ToString().ToLowerInvariant()
        RUN_DOCKER_PUBLISH = $RunDockerPublish.ToString().ToLowerInvariant()
        REGISTRY_IMAGE = $RegistryImage
        SKIP_CHECKOUT = $SkipCheckout.ToString().ToLowerInvariant()
        RUN_DEPLOY = $RunDeploy.ToString().ToLowerInvariant()
        INVENTORY_PATH = $InventoryPath
        ANSIBLE_EXTRA_VARS = $AnsibleExtraVars
        RUN_GITOPS_UPDATE = $RunGitOpsUpdate.ToString().ToLowerInvariant()
        GITOPS_VALUES_FILE = $GitOpsValuesFile
        GITOPS_TARGET_BRANCH = $GitOpsTargetBranch
        GITOPS_PUSH_REMOTE = $GitOpsPushRemote
        GIT_USER_NAME = $GitUserName
        GIT_USER_EMAIL = $GitUserEmail
        RUN_ARGOCD_SYNC = $RunArgoCdSync.ToString().ToLowerInvariant()
        ARGOCD_APP_NAME = $ArgoCdAppName
        ARGOCD_SYNC_MODE = $ArgoCdSyncMode
        ARGOCD_NAMESPACE = $ArgoCdNamespace
        ARGOCD_SERVER = $ArgoCdServer
        DASHBOARD_URL = $DashboardUrl
        K8S_DASHBOARD_URL = $K8sDashboardUrl
    }
}

foreach ($key in $AdditionalParameters.Keys) {
    $value = $AdditionalParameters[$key]
    if ($value -is [bool]) {
        $body[$key] = $value.ToString().ToLowerInvariant()
    }
    elseif ($null -eq $value) {
        $body[$key] = ""
    }
    else {
        $body[$key] = [string]$value
    }
}

try {
    Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/job/$encodedJobName/buildWithParameters" -Method Post -Headers $headers -WebSession $webSession -Body $body | Out-Null
}
catch {
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode.value__ -eq 400) {
        throw "Jenkins rejected buildWithParameters for '$JobName'. The job parameter definitions are likely out of date."
    }

    throw
}

Write-Host "Triggered Jenkins build #$targetBuildNumber for '$JobName'." -ForegroundColor Green

if (-not $WaitForCompletion) {
    if ($PassThru) {
        [pscustomobject]@{
            JobName = $JobName
            BuildNumber = $targetBuildNumber
            Result = "QUEUED"
        }
    }
    return
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 5
    try {
        $build = Invoke-RestMethod -Uri "$BaseUrl/job/$encodedJobName/$targetBuildNumber/api/json" -Headers $authHeaders -WebSession $webSession
    }
    catch {
        continue
    }

    if (-not $build.building -and $build.result) {
        Write-Host ("Build #{0} finished with result: {1}" -f $build.number, $build.result) -ForegroundColor Cyan
        if ($AcceptedResults -notcontains $build.result) {
            throw "Jenkins build failed with result $($build.result)."
        }
        if ($PassThru) {
            return [pscustomobject]@{
                JobName = $JobName
                BuildNumber = $build.number
                Result = $build.result
                Url = "$BaseUrl/job/$encodedJobName/$($build.number)/"
            }
        }
        return
    }
} while ((Get-Date) -lt $deadline)

throw "Timed out waiting for Jenkins build '$JobName' (#$targetBuildNumber) to finish."
