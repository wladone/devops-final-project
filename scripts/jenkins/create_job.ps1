param (
    [string]$JobName = "data-quality-monitor-local",
    [string]$BaseUrl = "http://localhost:8080",
    [ValidateSet("project", "orchestrator")]
    [string]$JobType = "project",
    [string]$PipelineFilePath = "",
    [string]$Description = ""
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

function Escape-Xml {
    param (
        [string]$Value
    )

    if ($null -eq $Value) {
        return ""
    }

    return [System.Security.SecurityElement]::Escape($Value)
}

function Get-ProjectPipelineParameters {
    return @(
        @{ Type = "string"; Name = "PROJECT_DIR"; Default = "."; Description = "Project directory relative to the Jenkins workspace or absolute path for a mounted local project" }
        @{ Type = "string"; Name = "INPUT_FILE"; Default = "data/raw/psq_customer_base_v8_stress.csv"; Description = "Input dataset path inside the repository" }
        @{ Type = "string"; Name = "RULES_FILE"; Default = "config/rules.yml"; Description = "Rules YAML path inside the repository" }
        @{ Type = "string"; Name = "OUTPUT_DIR"; Default = "reports/ci"; Description = "Directory for generated reports" }
        @{ Type = "boolean"; Name = "RUN_UNIT_TESTS"; Default = "true"; Description = "Run unit tests for the Python validation modules" }
        @{ Type = "boolean"; Name = "RUN_SONAR_SCAN"; Default = "false"; Description = "Run SonarQube analysis when the scanner and credentials are available" }
        @{ Type = "string"; Name = "SONAR_HOST_URL"; Default = ""; Description = "SonarQube or SonarQube Cloud URL" }
        @{ Type = "string"; Name = "SONAR_TOKEN_CREDENTIALS_ID"; Default = ""; Description = "Jenkins secret text credentials ID for the Sonar token" }
        @{ Type = "boolean"; Name = "RUN_DATA_QUALITY_JOB"; Default = "true"; Description = "Run the batch validation job and archive the generated reports" }
        @{ Type = "boolean"; Name = "RUN_HELM_VALIDATION"; Default = "false"; Description = "Render and lint the Helm chart for the target environment" }
        @{ Type = "string"; Name = "HELM_VALUES_FILE"; Default = "helm/data-quality-monitor/values-dev.yaml"; Description = "Environment values file used for Helm validation" }
        @{ Type = "string"; Name = "HELM_RELEASE_NAME"; Default = "data-quality-monitor"; Description = "Release name used for Helm templating" }
        @{ Type = "string"; Name = "HELM_NAMESPACE"; Default = "dq-monitor-dev"; Description = "Namespace used for Helm templating" }
        @{ Type = "string"; Name = "K8S_NAMESPACE"; Default = "dq-monitor-dev"; Description = "Kubernetes namespace used by local core-mode smoke tests and runner jobs" }
        @{ Type = "string"; Name = "K8S_RUNNER_CRONJOB"; Default = "data-quality-monitor-data-quality-monitor-runner"; Description = "CronJob name used to create the manual Kubernetes data-quality job" }
        @{ Type = "string"; Name = "K8S_DASHBOARD_RESOURCE"; Default = "svc/data-quality-monitor-data-quality-monitor-dashboard"; Description = "Kubernetes resource used for the dashboard port-forward smoke test" }
        @{ Type = "boolean"; Name = "RUN_TERRAFORM_VALIDATE"; Default = "false"; Description = "Run Terraform init -backend=false and validate for the selected environments" }
        @{ Type = "string"; Name = "TERRAFORM_ENVIRONMENTS"; Default = "dev staging prod"; Description = "Space separated Terraform environment folders to validate" }
        @{ Type = "string"; Name = "REGISTRY_IMAGE"; Default = ""; Description = "Optional registry/repository name, for example registry.example.com/data-quality-monitor" }
        @{ Type = "string"; Name = "IMAGE_TAG_OVERRIDE"; Default = ""; Description = "Optional prebuilt image tag to reuse instead of the current Jenkins build number" }
        @{ Type = "string"; Name = "REGISTRY_CREDENTIALS_ID"; Default = ""; Description = "Optional Jenkins credentials ID for the Docker registry" }
        @{ Type = "boolean"; Name = "RUN_DOCKER_BUILD"; Default = "true"; Description = "Build the Docker image for this run" }
        @{ Type = "boolean"; Name = "RUN_SECURITY_SCAN"; Default = "false"; Description = "Run Trivy filesystem and image scans" }
        @{ Type = "boolean"; Name = "RUN_DOCKER_PUBLISH"; Default = "true"; Description = "Push the Docker image after a successful build or when reusing an existing image tag" }
        @{ Type = "boolean"; Name = "SKIP_CHECKOUT"; Default = "false"; Description = "Skip SCM checkout when the project directory is already mounted on the Jenkins agent" }
        @{ Type = "boolean"; Name = "RUN_DEPLOY"; Default = "false"; Description = "Deploy to the Linux host using Ansible after a successful build" }
        @{ Type = "string"; Name = "INVENTORY_PATH"; Default = "ansible/inventory.ini"; Description = "Ansible inventory file" }
        @{ Type = "string"; Name = "SSH_CREDENTIALS_ID"; Default = ""; Description = "Optional Jenkins SSH credentials ID for Ansible deploy" }
        @{ Type = "string"; Name = "ANSIBLE_EXTRA_VARS"; Default = ""; Description = "Optional additional Ansible extra vars, for example dashboard_port=18501" }
        @{ Type = "boolean"; Name = "RUN_GITOPS_UPDATE"; Default = "false"; Description = "Update the target Helm values file with the new image tag and push the change to Git" }
        @{ Type = "string"; Name = "GITOPS_VALUES_FILE"; Default = "helm/data-quality-monitor/values-dev.yaml"; Description = "Helm values file updated for the target environment" }
        @{ Type = "string"; Name = "GITOPS_TARGET_BRANCH"; Default = "main"; Description = "Git branch that Argo CD watches" }
        @{ Type = "string"; Name = "GITOPS_PUSH_REMOTE"; Default = "origin"; Description = "Git remote used for the GitOps push" }
        @{ Type = "string"; Name = "GITOPS_PUSH_CREDENTIALS_ID"; Default = ""; Description = "Optional Jenkins SSH credentials ID used to push GitOps changes" }
        @{ Type = "string"; Name = "GIT_USER_NAME"; Default = "jenkins-bot"; Description = "Git author name used for GitOps commits" }
        @{ Type = "string"; Name = "GIT_USER_EMAIL"; Default = "jenkins@example.local"; Description = "Git author email used for GitOps commits" }
        @{ Type = "boolean"; Name = "RUN_ARGOCD_SYNC"; Default = "false"; Description = "Ask Argo CD to sync after the GitOps commit was pushed" }
        @{ Type = "string"; Name = "ARGOCD_APP_NAME"; Default = "data-quality-monitor-dev"; Description = "Argo CD application name to sync" }
        @{ Type = "string"; Name = "ARGOCD_SYNC_MODE"; Default = "server"; Description = "Sync mode: server or core for local kubectl-based sync" }
        @{ Type = "string"; Name = "ARGOCD_NAMESPACE"; Default = "argocd"; Description = "Namespace where the Argo CD Application lives when using core sync" }
        @{ Type = "string"; Name = "ARGOCD_SERVER"; Default = ""; Description = "Argo CD API server, for example argocd.example.com" }
        @{ Type = "string"; Name = "ARGOCD_AUTH_TOKEN_CREDENTIALS_ID"; Default = ""; Description = "Jenkins secret text credentials ID for the Argo CD auth token" }
        @{ Type = "string"; Name = "DASHBOARD_URL"; Default = ""; Description = "Optional classic dashboard URL for the smoke test after Ansible deploy" }
        @{ Type = "string"; Name = "K8S_DASHBOARD_URL"; Default = ""; Description = "Optional Kubernetes dashboard URL for the smoke test after Argo CD sync" }
    )
}

function Get-OrchestratorPipelineParameters {
    return @(
        @{ Type = "string"; Name = "FULL_JOB_NAME"; Default = "data-quality-monitor-full"; Description = "Jenkins job name used for quality and security" }
        @{ Type = "string"; Name = "DELIVERY_JOB_NAME"; Default = "data-quality-monitor-delivery"; Description = "Jenkins job name used for deploy and GitOps delivery" }
        @{ Type = "string"; Name = "FULL_PROJECT_DIR"; Default = "/workspace/data-quality-monitor"; Description = "Mounted project path used by the full sub-job" }
        @{ Type = "string"; Name = "DELIVERY_PROJECT_DIR"; Default = "/workspace/data-quality-monitor/.tmp/jenkins-gitops-source"; Description = "Mounted GitOps worktree path used by the delivery sub-job" }
        @{ Type = "string"; Name = "REGISTRY_IMAGE"; Default = "localhost:5001/data-quality-monitor"; Description = "Image repository used by both sub-jobs" }
        @{ Type = "string"; Name = "SONAR_PROJECT_KEY"; Default = "data-quality-monitor"; Description = "SonarQube project key to verify" }
        @{ Type = "string"; Name = "SONAR_TOKEN_CREDENTIALS_ID"; Default = "sonar-local-token"; Description = "Jenkins credentials ID for the SonarQube token" }
        @{ Type = "string"; Name = "ARGOCD_APP_NAME"; Default = "data-quality-monitor-kind"; Description = "Argo CD application name to verify" }
        @{ Type = "string"; Name = "ARGOCD_NAMESPACE"; Default = "argocd"; Description = "Namespace that contains the Argo CD Application" }
        @{ Type = "string"; Name = "K8S_NAMESPACE"; Default = "dq-monitor-dev"; Description = "Kubernetes namespace used by the demo app" }
        @{ Type = "string"; Name = "K8S_RUNNER_CRONJOB"; Default = "data-quality-monitor-data-quality-monitor-runner"; Description = "CronJob name used for manual Kubernetes data-quality runs" }
        @{ Type = "string"; Name = "K8S_DASHBOARD_RESOURCE"; Default = "svc/data-quality-monitor-data-quality-monitor-dashboard"; Description = "Kubernetes dashboard service/resource used for smoke testing" }
        @{ Type = "string"; Name = "PUBLIC_JENKINS_BASE_URL"; Default = "http://localhost:8080"; Description = "User-facing Jenkins base URL used in demo links" }
        @{ Type = "string"; Name = "PUBLIC_SONAR_URL"; Default = "http://localhost:9000"; Description = "User-facing SonarQube URL used in demo links" }
        @{ Type = "string"; Name = "PUBLIC_ARGOCD_URL"; Default = "https://127.0.0.1:28080"; Description = "User-facing Argo CD URL used in demo links" }
        @{ Type = "string"; Name = "PUBLIC_GRAFANA_URL"; Default = "http://localhost:3000"; Description = "User-facing Grafana URL used in demo links" }
        @{ Type = "string"; Name = "PUBLIC_PROMETHEUS_URL"; Default = "http://localhost:9090"; Description = "User-facing Prometheus URL used in demo links" }
        @{ Type = "string"; Name = "PUBLIC_CLASSIC_DASHBOARD_URL"; Default = "http://localhost:18501"; Description = "User-facing classic dashboard URL used in demo links" }
        @{ Type = "string"; Name = "PUBLIC_K8S_DASHBOARD_URL"; Default = "http://127.0.0.1:28501"; Description = "User-facing Kubernetes dashboard URL used in demo links" }
        @{ Type = "string"; Name = "INTERNAL_REGISTRY_BASE_URL"; Default = "http://host.docker.internal:5001"; Description = "Registry URL reachable from inside the Jenkins container" }
        @{ Type = "string"; Name = "INTERNAL_SONAR_URL"; Default = "http://sonarqube:9000"; Description = "SonarQube URL reachable from inside the Jenkins container" }
        @{ Type = "string"; Name = "INTERNAL_CLASSIC_DASHBOARD_URL"; Default = "http://host.docker.internal:18501"; Description = "Classic dashboard URL reachable from inside the Jenkins container" }
        @{ Type = "string"; Name = "INTERNAL_K8S_DASHBOARD_URL"; Default = "http://host.docker.internal:28501"; Description = "Kubernetes dashboard URL reachable from inside the Jenkins container" }
        @{ Type = "string"; Name = "INTERNAL_GRAFANA_URL"; Default = "http://host.docker.internal:3000"; Description = "Grafana URL reachable from inside the Jenkins container" }
        @{ Type = "string"; Name = "INTERNAL_PROMETHEUS_READY_URL"; Default = "http://host.docker.internal:9090/-/ready"; Description = "Prometheus readiness URL reachable from inside the Jenkins container" }
    )
}

function Convert-ParameterDefinitionsToXml {
    param (
        [object[]]$Definitions
    )

    if (-not $Definitions -or $Definitions.Count -eq 0) {
        return "<properties/>"
    }

    $parameterXml = foreach ($definition in $Definitions) {
        $name = Escape-Xml $definition.Name
        $description = Escape-Xml $definition.Description
        $defaultValue = Escape-Xml $definition.Default

        if ($definition.Type -eq "boolean") {
@"
      <hudson.model.BooleanParameterDefinition>
        <name>$name</name>
        <description>$description</description>
        <defaultValue>$defaultValue</defaultValue>
      </hudson.model.BooleanParameterDefinition>
"@
        }
        else {
@"
      <hudson.model.StringParameterDefinition>
        <name>$name</name>
        <description>$description</description>
        <defaultValue>$defaultValue</defaultValue>
        <trim>false</trim>
      </hudson.model.StringParameterDefinition>
"@
        }
    }

@"
  <properties>
    <hudson.model.ParametersDefinitionProperty>
      <parameterDefinitions>
$($parameterXml -join "`n")
      </parameterDefinitions>
    </hudson.model.ParametersDefinitionProperty>
  </properties>
"@
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$settings = Get-JenkinsSettings
$userName = $settings["JENKINS_ADMIN_ID"]
$password = $settings["JENKINS_ADMIN_PASSWORD"]
$authHeaders = Get-JenkinsAuthHeader -UserName $userName -Password $password
$webContext = Get-JenkinsWebSessionContext -BaseUrl $BaseUrl -AuthHeaders $authHeaders
$headers = $webContext.Headers
$webSession = $webContext.WebSession

$resolvedPipelineFilePath = if ($PipelineFilePath) {
    Join-Path $repoRoot $PipelineFilePath
}
elseif ($JobType -eq "orchestrator") {
    Join-Path $repoRoot "jenkins\Jenkinsfile.demo-e2e"
}
else {
    Join-Path $repoRoot "Jenkinsfile"
}

$resolvedDescription = if ($Description) {
    $Description
}
elseif ($JobType -eq "orchestrator") {
    "Orchestrator pipeline for the full local DevOps demo."
}
else {
    "Local pipeline for the Data Quality Monitoring project."
}

$parameterDefinitions = if ($JobType -eq "orchestrator") {
    Get-OrchestratorPipelineParameters
}
else {
    Get-ProjectPipelineParameters
}

$propertiesXml = Convert-ParameterDefinitionsToXml -Definitions $parameterDefinitions
$jenkinsfilePath = $resolvedPipelineFilePath
$pipelineScript = Get-Content $jenkinsfilePath -Raw
$escapedScript = Escape-Xml $pipelineScript
$escapedDescription = Escape-Xml $resolvedDescription

$jobXml = @"
<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <actions/>
  <description>$escapedDescription</description>
  <keepDependencies>false</keepDependencies>
$propertiesXml
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>$escapedScript</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>
"@

$encodedJobName = [uri]::EscapeDataString($JobName)
$jobUrl = "$BaseUrl/job/$encodedJobName/api/json"
$jobsApiUrl = "$BaseUrl/api/json?tree=jobs[name]"

try {
    $jobs = Invoke-RestMethod -Uri $jobsApiUrl -Headers $authHeaders -WebSession $webSession
    $jobExists = $false
    foreach ($job in $jobs.jobs) {
        if ($job.name -eq $JobName) {
            $jobExists = $true
            break
        }
    }

    if ($jobExists) {
        Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/job/$encodedJobName/config.xml" -Method Post -Headers $headers -WebSession $webSession -ContentType "application/xml" -Body $jobXml | Out-Null
        Write-Host "Updated Jenkins job '$JobName'." -ForegroundColor Green
    }
    else {
        Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/createItem?name=$encodedJobName" -Method Post -Headers $headers -WebSession $webSession -ContentType "application/xml" -Body $jobXml | Out-Null
        Write-Host "Created Jenkins job '$JobName'." -ForegroundColor Green
    }
}
catch {
    throw
}
