param (
    [string]$InstallDir = (Join-Path $HOME "bin")
)

$ErrorActionPreference = "Stop"

$downloadsDir = Join-Path $env:TEMP "dq-devops-tools"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $downloadsDir -Force | Out-Null

function Install-DockerWrapper {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $wrapperPath = Join-Path $InstallDir ($Name + ".cmd")
    Set-Content -Path $wrapperPath -Value $Content -Encoding ASCII
    return $wrapperPath
}

$tools = @(
    @{
        Name = "kind"
        Url = "https://kind.sigs.k8s.io/dl/v0.24.0/kind-windows-amd64"
        Archive = $false
        Output = "kind.exe"
    },
    @{
        Name = "helm"
        Url = "https://get.helm.sh/helm-v3.16.4-windows-amd64.zip"
        Archive = $true
        InnerPath = "windows-amd64\helm.exe"
        Output = "helm.exe"
    },
    @{
        Name = "terraform"
        Url = "https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_windows_amd64.zip"
        Archive = $true
        InnerPath = "terraform.exe"
        Output = "terraform.exe"
    },
    @{
        Name = "trivy"
        Url = "https://github.com/aquasecurity/trivy/releases/download/v0.59.1/trivy_0.59.1_windows-64bit.zip"
        Archive = $true
        InnerPath = "trivy.exe"
        Output = "trivy.exe"
        DockerWrapper = @'
@echo off
docker run --rm -v "%CD%:/workspace" -w /workspace aquasec/trivy:0.59.1 %*
'@
    },
    @{
        Name = "argocd"
        Url = "https://github.com/argoproj/argo-cd/releases/download/v2.13.3/argocd-windows-amd64.exe"
        Archive = $false
        Output = "argocd.exe"
        DockerWrapper = @'
@echo off
docker run --rm -v "%USERPROFILE%\.kube:/root/.kube" -v "%USERPROFILE%\.config\argocd:/root/.config/argocd" quay.io/argoproj/argocd:v2.13.3 %*
'@
    }
)

foreach ($tool in $tools) {
    $destination = Join-Path $InstallDir $tool.Output
    $downloadPath = Join-Path $downloadsDir ([IO.Path]::GetFileName($tool.Url))

    Write-Host "Installing $($tool.Name)..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $tool.Url -OutFile $downloadPath

        if ($tool.Archive) {
            $extractDir = Join-Path $downloadsDir ("extract-" + $tool.Name)
            if (Test-Path $extractDir) {
                Remove-Item $extractDir -Recurse -Force
            }
            Expand-Archive -Path $downloadPath -DestinationPath $extractDir -Force
            Copy-Item -Path (Join-Path $extractDir $tool.InnerPath) -Destination $destination -Force
        }
        else {
            Copy-Item -Path $downloadPath -Destination $destination -Force
        }

        Write-Host "Installed native binary for $($tool.Name)." -ForegroundColor Green
    }
    catch {
        if (-not $tool.ContainsKey("DockerWrapper")) {
            throw
        }

        $wrapperPath = Install-DockerWrapper -Name $tool.Name -Content $tool.DockerWrapper
        Write-Host "Fell back to Docker wrapper for $($tool.Name): $wrapperPath" -ForegroundColor Yellow
    }
}

$currentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = @()
if ($currentUserPath) {
    $pathEntries = $currentUserPath.Split(';', [System.StringSplitOptions]::RemoveEmptyEntries)
}

if ($pathEntries -notcontains $InstallDir) {
    $newPath = ($pathEntries + $InstallDir) -join ';'
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Added $InstallDir to the user PATH. Open a new terminal after this command." -ForegroundColor Yellow
}

Write-Host "Installed tools into $InstallDir" -ForegroundColor Green
