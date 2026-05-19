$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

function Test-Command {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "Checking local prerequisites for Data Quality Monitoring..." -ForegroundColor Cyan

$projectPython = Get-ProjectPython

$checks = @(
    @{
        Name = "Python"
        Installed = ($null -ne $projectPython)
        Hint = "Install Python 3.11+ or set PROJECT_PYTHON to a valid interpreter path."
    },
    @{
        Name = "Docker CLI"
        Installed = (Test-Command -Name "docker")
        Hint = "Install Docker Desktop."
    },
    @{
        Name = "VS Code"
        Installed = (Test-Path "$env:LOCALAPPDATA\Programs\Microsoft VS Code\Code.exe")
        Hint = "Install Visual Studio Code."
    },
    @{
        Name = "WSL"
        Installed = (Test-Path "$env:WINDIR\System32\wsl.exe")
        Hint = "Install WSL2 with Ubuntu for a smoother Linux-like workflow."
    }
)

foreach ($check in $checks) {
    if ($check.Installed) {
        Write-Host ("[OK] " + $check.Name) -ForegroundColor Green
    }
    else {
        Write-Host ("[MISSING] " + $check.Name) -ForegroundColor Yellow
        Write-Host ("          " + $check.Hint) -ForegroundColor DarkYellow
    }
}

if (Test-Command -Name "docker") {
    try {
        docker info --format "{{.ServerVersion}}" *> $null
        Write-Host "[OK] Docker daemon is running" -ForegroundColor Green
    }
    catch {
        Write-Host "[INFO] Docker CLI exists, but Docker Desktop does not seem to be running." -ForegroundColor Yellow
    }
}

if ($projectPython) {
    Write-Host ("[INFO] Project Python: " + $projectPython) -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Next recommended step:" -ForegroundColor Cyan
Write-Host "1. Ensure Python is installed or set PROJECT_PYTHON" -ForegroundColor White
Write-Host "2. Run .\scripts\setup_venv.ps1" -ForegroundColor White
Write-Host "3. Run .\scripts\run_pipeline.ps1" -ForegroundColor White
Write-Host "4. Run .\scripts\run_dashboard.ps1" -ForegroundColor White
