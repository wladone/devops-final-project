param (
    [string]$RepoName = "data-quality-monitor",
    [string]$DefaultBranch = "main"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$gitopsRoot = Join-Path $repoRoot "lab\gitops"
$reposDir = Join-Path $gitopsRoot "repos"
$bareRepoDir = Join-Path $reposDir "$RepoName.git"
$workDir = Join-Path $repoRoot ".tmp\gitops-workdir"

New-Item -ItemType Directory -Path $reposDir -Force | Out-Null
if (Test-Path $workDir) {
    Remove-Item $workDir -Recurse -Force
}
New-Item -ItemType Directory -Path $workDir -Force | Out-Null

$robocopyLog = Join-Path $repoRoot ".tmp\gitops-robocopy.log"
$null = robocopy $repoRoot $workDir /MIR /NFL /NDL /NJH /NJS /NP /R:2 /W:1 `
    /XD ".git" ".venv" ".tmp" "logs" "htmlcov" "__pycache__" ".pytest_cache" ".mypy_cache" "lab\gitops\repos" `
    /XD "reports\latest" "reports\ci" `
    /XF "jenkins\.env" ".env" `
    /LOG:$robocopyLog
$robocopyExit = $LASTEXITCODE
if ($robocopyExit -ge 8) {
    throw "robocopy failed with exit code $robocopyExit"
}

if (Test-Path (Join-Path $workDir ".git")) {
    Remove-Item (Join-Path $workDir ".git") -Recurse -Force
}

Push-Location $workDir
try {
    if (Test-Path $bareRepoDir) {
        Remove-Item $bareRepoDir -Recurse -Force
    }

    # Run all git invocations under a relaxed error preference for this block
    # because git writes benign info to stderr (CRLF warnings, push summary)
    # which PowerShell 5.1 otherwise escalates to terminating errors.
    $previousErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & git init -b $DefaultBranch *>$null
    & git config user.name "gitops-bot"
    & git config user.email "gitops@example.local"
    & git config core.safecrlf false
    & git add . *>$null
    & git commit -m "Bootstrap local GitOps repository" *>$null
    & git init --bare $bareRepoDir *>$null
    & git --git-dir=$bareRepoDir symbolic-ref HEAD "refs/heads/$DefaultBranch"
    & git remote add origin $bareRepoDir
    & git push --force origin $DefaultBranch *>$null
    & git --git-dir=$bareRepoDir update-server-info
    $ErrorActionPreference = $previousErrorPreference
}
finally {
    Pop-Location
}

$images = docker images --format "{{.Repository}}:{{.Tag}}" "localhost:5001/data-quality-monitor"
$sourceImage = $images | Where-Object { $_ -notmatch "<none>" -and $_ -ne "localhost:5001/data-quality-monitor:latest" } | Select-Object -First 1
if ($sourceImage) {
    docker tag $sourceImage "localhost:5001/data-quality-monitor:latest"
    docker push "localhost:5001/data-quality-monitor:latest" | Out-Null
}

Write-Host "Local GitOps repository is ready at $bareRepoDir" -ForegroundColor Green
Write-Host "Served as git://localhost:9418/$RepoName.git" -ForegroundColor Cyan
