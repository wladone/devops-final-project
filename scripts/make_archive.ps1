# make_archive.ps1 -- Package the project as a single zip for evaluator delivery.
#
# Excludes:
#   * Generated state and caches (.venv, .git, __pycache__, .pytest_cache,
#     .hypothesis, .scannerwork, .tmp, .terraform, logs, output)
#   * Regenerable artefacts (data/db, data/processed, data/stress, reports/)
# Includes:
#   * All source under src/, dashboard/, scripts/, tests/, ansible/, helm/,
#     terraform/, argocd/, jenkins/, lab/, monitoring/, security/, config/,
#     docs/, notebooks/
#   * Top-level configs: Dockerfile, docker-compose.yml, Jenkinsfile,
#     requirements*.txt, README, dq.ps1/dq.cmd, .gitignore, .gitattributes
#
# Output: ./dist/data-quality-monitor-<git-short-sha>.zip (or -nogit suffix)
#
# Usage:
#   .\scripts\make_archive.ps1
#   .\scripts\make_archive.ps1 -OutputName custom-name.zip
#   .\scripts\make_archive.ps1 -SkipSampleReport

[CmdletBinding()]
param (
    [string]$OutputName = "",
    [switch]$SkipSampleReport
)

$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$repoRoot = (Resolve-Path "$PSScriptRoot/..").Path
Set-Location $repoRoot

Write-Host "Packaging from $repoRoot" -ForegroundColor Cyan

# --- Resolve an output name -------------------------------------------------

if (-not $OutputName) {
    try {
        $sha = (git rev-parse --short HEAD 2>$null).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $sha) { $sha = "nogit" }
    } catch { $sha = "nogit" }
    $OutputName = "data-quality-monitor-$sha.zip"
}

$distDir = Join-Path $repoRoot "dist"
New-Item -ItemType Directory -Path $distDir -Force | Out-Null
$archivePath = Join-Path $distDir $OutputName

if (Test-Path $archivePath) {
    Remove-Item $archivePath -Force
    Write-Host "Removed previous archive: $archivePath" -ForegroundColor Yellow
}

# --- Optional: regenerate a fresh sample report -----------------------------

if (-not $SkipSampleReport) {
    Write-Host "Generating fresh sample report (reports/latest/) ..." -ForegroundColor Cyan
    $env:PYTHONPATH = Join-Path $repoRoot "src"
    $python = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) { $python = "python" }
    & $python src/main.py --input data/raw/psq_customer_base_v8_stress.csv `
        --rules config/rules.yml --output-dir reports/latest 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Sample report refreshed in reports/latest/" -ForegroundColor Green
    } else {
        Write-Host "  Sample report generation failed (continuing without)" -ForegroundColor Yellow
    }
}

# --- Build the file list ---------------------------------------------------
# Exclusion is path-based on the full FullName. Each entry is a regex tested
# against the path *with forward slashes* so the rule reads naturally.

$excludePatterns = @(
    '/\.venv(/|$)',
    '/\.git(/|$)',
    '/__pycache__(/|$)',
    '/\.pytest_cache(/|$)',
    '/\.hypothesis(/|$)',
    '/\.scannerwork(/|$)',
    '/\.tmp(/|$)',
    '/\.claude(/|$)',
    '/\.playwright-cli(/|$)',
    '/\.terraform(/|$)',
    '/\.terraform\.lock\.hcl$',
    '/logs(/|$)',
    '/output(/|$)',
    '/dist(/|$)',
    '/node_modules(/|$)',
    '/data/db(/|$)',
    '/data/processed(/|$)',
    '/data/stress(/|$)',
    '/reports/(ci|stress|stress-ci-check|quality-ladder|quality-ladder-ci-check|quality-ladder-data|sparrowhawk_|docker_|run_|e2e|sql-sourced)(/|$|.*)',
    '\.pyc$',
    '\.pyo$',
    '\.tfstate(\..*)?$',
    'crash\.log$'
)

function Should-Include {
    param ([string]$Path)
    $unix = ($Path -replace '\\', '/')
    foreach ($p in $excludePatterns) {
        if ($unix -match $p) { return $false }
    }
    return $true
}

Write-Host "Collecting files ..." -ForegroundColor Cyan
$allFiles = Get-ChildItem -Path $repoRoot -Recurse -File -Force |
    Where-Object { Should-Include $_.FullName }
$totalBytes = ($allFiles | Measure-Object -Property Length -Sum).Sum
$totalMB = [math]::Round($totalBytes / 1MB, 2)
Write-Host "  $($allFiles.Count) files, $totalMB MB uncompressed" -ForegroundColor Gray

# --- Stage into a temp dir + zip ------------------------------------------

$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("dq-pkg-" + [Guid]::NewGuid().ToString("N").Substring(0,8))
$stageProject = Join-Path $stagingRoot "data-quality-monitor"
New-Item -ItemType Directory -Path $stageProject -Force | Out-Null

Write-Host "Staging to $stageProject ..." -ForegroundColor Cyan
foreach ($file in $allFiles) {
    $relative = $file.FullName.Substring($repoRoot.Length).TrimStart('\','/')
    $target = Join-Path $stageProject $relative
    $targetDir = Split-Path -Parent $target
    if (-not (Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }
    Copy-Item -Path $file.FullName -Destination $target -Force
}

Write-Host "Compressing ..." -ForegroundColor Cyan
Compress-Archive -Path "$stageProject" -DestinationPath $archivePath -CompressionLevel Optimal -Force

Remove-Item -Recurse -Force $stagingRoot

$archiveBytes = (Get-Item $archivePath).Length
$archiveMB = [math]::Round($archiveBytes / 1MB, 2)
$sha256 = (Get-FileHash -Algorithm SHA256 -Path $archivePath).Hash

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host " Archive ready" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host " Path:    $archivePath"
Write-Host " Size:    $archiveMB MB"
Write-Host " SHA-256: $sha256"
Write-Host " Files:   $($allFiles.Count)"
Write-Host ""
Write-Host " Sanity check before emailing:" -ForegroundColor Cyan
Write-Host "   1. Expand-Archive '$archivePath' -DestinationPath \$env:TEMP\dq-check"
Write-Host "   2. cd \$env:TEMP\dq-check\data-quality-monitor"
Write-Host "   3. .\scripts\setup_venv.ps1 ; .\scripts\run_tests.ps1"
