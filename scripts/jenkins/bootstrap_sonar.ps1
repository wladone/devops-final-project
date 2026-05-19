param (
    [string]$BaseUrl = "http://localhost:8080",
    [string]$SonarUrl = "http://localhost:9000",
    [string]$CredentialId = "sonar-local-token",
    [string]$ProjectKey = "data-quality-monitor",
    [string]$ProjectName = "Data Quality Monitoring",
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = "Stop"

. "$PSScriptRoot/common.ps1"

function New-BasicAuthHeader {
    param (
        [string]$UserName,
        [string]$Password = ""
    )

    $pair = "{0}:{1}" -f $UserName, $Password
    $bytes = [System.Text.Encoding]::ASCII.GetBytes($pair)
    $token = [Convert]::ToBase64String($bytes)
    return @{ Authorization = "Basic $token" }
}

function Invoke-SonarApi {
    param (
        [string]$Url,
        [string]$Method = "Get",
        [hashtable]$Headers,
        [hashtable]$Body
    )

    $request = @{
        Uri = $Url
        Method = $Method
        Headers = $Headers
        TimeoutSec = 30
    }

    if ($Body) {
        $request.Body = $Body
    }

    return Invoke-RestMethod @request
}

function Test-SonarCredentials {
    param (
        [hashtable]$Headers
    )

    try {
        $response = Invoke-SonarApi -Url "$SonarUrl/api/authentication/validate" -Headers $Headers
        return [bool]$response.valid
    }
    catch {
        return $false
    }
}

function Ensure-SonarDemoQualityGate {
    param (
        [hashtable]$Headers,
        [string]$GateName = "Local Demo Advisory Gate"
    )

    $gates = Invoke-SonarApi -Url "$SonarUrl/api/qualitygates/list" -Headers $Headers
    $existingGate = $null
    foreach ($gate in @($gates.qualitygates)) {
        if ($gate.name -eq $GateName) {
            $existingGate = $gate
            break
        }
    }

    if (-not $existingGate) {
        Invoke-SonarApi -Url "$SonarUrl/api/qualitygates/create" -Method Post -Headers $Headers -Body @{
            name = $GateName
        } | Out-Null
    }

    Invoke-SonarApi -Url "$SonarUrl/api/qualitygates/select" -Method Post -Headers $Headers -Body @{
        projectKey = $ProjectKey
        gateName = $GateName
    } | Out-Null

    $encodedGateName = [uri]::EscapeDataString($GateName)
    $gateDetails = Invoke-SonarApi -Url "$SonarUrl/api/qualitygates/show?name=$encodedGateName" -Headers $Headers
    foreach ($condition in @($gateDetails.conditions)) {
        if ($condition.metric -in @("new_coverage", "new_security_hotspots_reviewed")) {
            Invoke-SonarApi -Url "$SonarUrl/api/qualitygates/delete_condition" -Method Post -Headers $Headers -Body @{
                id = $condition.id
            } | Out-Null
        }
    }

    return $GateName
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$tmpDir = Join-Path $repoRoot ".tmp"
$tokenFile = Join-Path $tmpDir "sonar-local-token.txt"
$settings = Get-JenkinsSettings
$jenkinsUser = $settings["JENKINS_ADMIN_ID"]
$jenkinsPassword = $settings["JENKINS_ADMIN_PASSWORD"]
$sonarAdminPassword = if ($settings.ContainsKey("SONARQUBE_ADMIN_PASSWORD") -and $settings["SONARQUBE_ADMIN_PASSWORD"]) {
    $settings["SONARQUBE_ADMIN_PASSWORD"]
} else {
    "admin123!"
}
$sonarTokenName = if ($settings.ContainsKey("SONARQUBE_TOKEN_NAME") -and $settings["SONARQUBE_TOKEN_NAME"]) {
    $settings["SONARQUBE_TOKEN_NAME"]
} else {
    "jenkins-local-token"
}

New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    try {
        $status = Invoke-SonarApi -Url "$SonarUrl/api/system/status" -Headers (New-BasicAuthHeader -UserName "admin" -Password "admin")
        if ($status.status -eq "UP") {
            break
        }
    }
    catch {
    }

    Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)

if ((Get-Date) -ge $deadline) {
    throw "SonarQube did not become reachable at $SonarUrl in time."
}

$adminHeaders = $null
$configuredHeaders = New-BasicAuthHeader -UserName "admin" -Password $sonarAdminPassword
$defaultHeaders = New-BasicAuthHeader -UserName "admin" -Password "admin"

if (Test-SonarCredentials -Headers $configuredHeaders) {
    $adminHeaders = $configuredHeaders
}
elseif (Test-SonarCredentials -Headers $defaultHeaders) {
    if ($sonarAdminPassword -ne "admin") {
        Invoke-SonarApi -Url "$SonarUrl/api/users/change_password" -Method Post -Headers $defaultHeaders -Body @{
            login = "admin"
            previousPassword = "admin"
            password = $sonarAdminPassword
        } | Out-Null
        $adminHeaders = New-BasicAuthHeader -UserName "admin" -Password $sonarAdminPassword
    }
    else {
        $adminHeaders = $defaultHeaders
    }
}
else {
    throw "Could not authenticate to SonarQube with the configured or default admin credentials."
}

$projectSearch = Invoke-SonarApi -Url "$SonarUrl/api/projects/search?projects=$ProjectKey" -Headers $adminHeaders
if (-not $projectSearch.components -or $projectSearch.components.Count -eq 0) {
    Invoke-SonarApi -Url "$SonarUrl/api/projects/create" -Method Post -Headers $adminHeaders -Body @{
        project = $ProjectKey
        name = $ProjectName
    } | Out-Null
}

$qualityGateName = Ensure-SonarDemoQualityGate -Headers $adminHeaders

$sonarToken = ""
if (Test-Path $tokenFile) {
    $candidateToken = (Get-Content $tokenFile -Raw).Trim()
    if ($candidateToken -and (Test-SonarCredentials -Headers (New-BasicAuthHeader -UserName $candidateToken))) {
        $sonarToken = $candidateToken
    }
}

if (-not $sonarToken) {
    try {
        $tokenList = Invoke-SonarApi -Url "$SonarUrl/api/user_tokens/search" -Headers $adminHeaders
        if ($tokenList.userTokens) {
            foreach ($token in $tokenList.userTokens) {
                if ($token.name -eq $sonarTokenName) {
                    Invoke-SonarApi -Url "$SonarUrl/api/user_tokens/revoke" -Method Post -Headers $adminHeaders -Body @{ name = $sonarTokenName } | Out-Null
                    break
                }
            }
        }
    }
    catch {
    }

    $tokenResponse = Invoke-SonarApi -Url "$SonarUrl/api/user_tokens/generate" -Method Post -Headers $adminHeaders -Body @{
        name = $sonarTokenName
    }
    $sonarToken = $tokenResponse.token
    Set-Content -Path $tokenFile -Value $sonarToken -Encoding ASCII
}

Set-JenkinsStringCredential -BaseUrl $BaseUrl -UserName $jenkinsUser -Password $jenkinsPassword -CredentialId $CredentialId -SecretValue $sonarToken -Description "Local SonarQube token for the full demo"

Write-Host "SonarQube is ready at $SonarUrl" -ForegroundColor Green
Write-Host "SonarQube project: $ProjectKey" -ForegroundColor Cyan
Write-Host "SonarQube quality gate: $qualityGateName" -ForegroundColor Cyan
Write-Host "Jenkins credential updated: $CredentialId" -ForegroundColor Cyan
