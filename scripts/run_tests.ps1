$ErrorActionPreference = "Stop"

. "$PSScriptRoot/common.ps1"

$pythonExe = Get-VenvPython -ProjectRoot $PWD
if (-not $pythonExe) {
    Write-Error "Virtual environment not found. Run .\scripts\setup_venv.ps1 first."
}

$env:PYTHONPATH = (Join-Path $PWD "src")

& $pythonExe -m pytest

if ($LASTEXITCODE -ne 0) {
    Write-Error "Test execution failed."
}
