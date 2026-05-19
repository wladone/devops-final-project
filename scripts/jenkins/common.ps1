function Get-JenkinsSettings {
    param (
        [string]$EnvFilePath = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..\..")) "jenkins\.env")
    )

    $settings = @{}
    Get-Content $EnvFilePath | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            $settings[$parts[0]] = $parts[1]
        }
    }

    return $settings
}

function Get-JenkinsAuthHeader {
    param (
        [string]$UserName,
        [string]$Password
    )

    $pair = "{0}:{1}" -f $UserName, $Password
    $bytes = [System.Text.Encoding]::ASCII.GetBytes($pair)
    $token = [Convert]::ToBase64String($bytes)
    return @{ Authorization = "Basic $token" }
}

function Get-JenkinsWebSessionContext {
    param (
        [string]$BaseUrl,
        [hashtable]$AuthHeaders
    )

    $crumbResponse = Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/crumbIssuer/api/json" -Headers $AuthHeaders -SessionVariable webSession
    $crumb = $crumbResponse.Content | ConvertFrom-Json
    $headers = @{}
    foreach ($key in $AuthHeaders.Keys) {
        $headers[$key] = $AuthHeaders[$key]
    }
    $headers[$crumb.crumbRequestField] = $crumb.crumb
    return @{
        Headers = $headers
        WebSession = $webSession
    }
}

function Invoke-JenkinsGroovyScript {
    param (
        [string]$BaseUrl,
        [string]$UserName,
        [string]$Password,
        [string]$Script
    )

    $authHeaders = Get-JenkinsAuthHeader -UserName $UserName -Password $Password
    $webContext = Get-JenkinsWebSessionContext -BaseUrl $BaseUrl -AuthHeaders $authHeaders
    $body = @{ script = $Script }
    return Invoke-RestMethod -Uri "$BaseUrl/scriptText" -Method Post -Headers $webContext.Headers -WebSession $webContext.WebSession -Body $body
}

function Set-JenkinsStringCredential {
    param (
        [string]$BaseUrl,
        [string]$UserName,
        [string]$Password,
        [string]$CredentialId,
        [string]$SecretValue,
        [string]$Description = ""
    )

    $safeId = $CredentialId.Replace('\', '\\').Replace("'", "\'")
    $safeSecret = $SecretValue.Replace('\', '\\').Replace("'", "\'")
    $safeDescription = $Description.Replace('\', '\\').Replace("'", "\'")

    $groovy = @"
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.CredentialsProvider
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.domains.Domain
import hudson.util.Secret
import jenkins.model.Jenkins
import org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl

def jenkins = Jenkins.get()
def store = jenkins.getExtensionList(SystemCredentialsProvider.class)[0].getStore()
def domain = Domain.global()
def existing = CredentialsProvider.lookupCredentials(
  org.jenkinsci.plugins.plaincredentials.StringCredentials.class,
  jenkins,
  null,
  null
).find { it.id == '$safeId' }
def replacement = new StringCredentialsImpl(
  CredentialsScope.GLOBAL,
  '$safeId',
  '$safeDescription',
  Secret.fromString('$safeSecret')
)

if (existing != null) {
  store.updateCredentials(domain, existing, replacement)
  println('UPDATED')
} else {
  store.addCredentials(domain, replacement)
  println('CREATED')
}
"@

    Invoke-JenkinsGroovyScript -BaseUrl $BaseUrl -UserName $UserName -Password $Password -Script $groovy | Out-Null
}
