$ErrorActionPreference = "Stop"
. "$PSScriptRoot/common.ps1"

$projectPython = Get-ProjectPython
if (-not $projectPython) {
    Write-Error "Python was not found. Install Python 3.11+ or set PROJECT_PYTHON to a valid interpreter path."
}

$tempDir = Join-Path $PWD ".tmp"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
$env:TEMP = $tempDir
$env:TMP = $tempDir

if ($projectPython -match "\.exe$") {
    & $projectPython -m venv .venv
}
else {
    Invoke-Expression "$projectPython -m venv .venv"
}

$pythonExe = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Error "Virtual environment was not created successfully."
}

& $pythonExe -m ensurepip --default-pip
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip could not be bootstrapped inside the virtual environment."
}

& $pythonExe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Error "pip upgrade failed."
}

& $pythonExe -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Dependency installation failed."
}

Write-Host "Virtual environment is ready." -ForegroundColor Green
Write-Host "Use '.\.venv\Scripts\Activate.ps1' to activate it." -ForegroundColor Cyan
