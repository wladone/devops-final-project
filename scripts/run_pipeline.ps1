$ErrorActionPreference = "Stop"

. "$PSScriptRoot/common.ps1"

$pythonExe = Get-VenvPython -ProjectRoot $PWD
if (-not $pythonExe) {
    Write-Error "Virtual environment not found. Run .\scripts\setup_venv.ps1 first."
}

$env:PYTHONPATH = (Join-Path $PWD "src")

& $pythonExe "src/main.py" `
    --input "data/raw/psq_customer_base_v8_stress.csv" `
    --rules "config/rules.yml" `
    --output-dir "reports/latest"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Pipeline execution failed."
}

Write-Host "Pipeline finished. Check reports/latest for outputs." -ForegroundColor Green
