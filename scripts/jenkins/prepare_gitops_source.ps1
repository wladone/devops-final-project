param (
    [string]$CloneDir = ".tmp\\jenkins-gitops-source",
    [string]$LocalBareRepo = "lab\\gitops\\repos\\data-quality-monitor.git",
    [string]$ContainerGitRemote = "git://host.docker.internal:9418/data-quality-monitor.git"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$clonePath = Join-Path $repoRoot $CloneDir

& (Join-Path $repoRoot "scripts\gitops\bootstrap_local_repo.ps1")

$bareRepoPath = Resolve-Path (Join-Path $repoRoot $LocalBareRepo)

if (Test-Path (Join-Path $clonePath ".git")) {
    Push-Location $clonePath
    try {
        git remote set-url origin $bareRepoPath
        git fetch origin main | Out-Null
        git reset --hard origin/main | Out-Null
        git clean -fd -e .venv | Out-Null
        git remote set-url origin $ContainerGitRemote
    }
    finally {
        Pop-Location
    }
}
else {
    if (Test-Path $clonePath) {
        Remove-Item $clonePath -Recurse -Force
    }

    git clone --branch main $bareRepoPath $clonePath | Out-Null
    Push-Location $clonePath
    try {
        git remote set-url origin $ContainerGitRemote
    }
    finally {
        Pop-Location
    }
}

Get-ChildItem -Path $clonePath -Recurse -Filter *.sh | ForEach-Object {
    $content = [IO.File]::ReadAllText($_.FullName)
    $normalized = $content -replace "`r`n", "`n"
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($_.FullName, $normalized, $encoding)
}

[pscustomobject]@{
    ClonePath = $clonePath
    BareRepoPath = $bareRepoPath
    ContainerProjectDir = "/workspace/data-quality-monitor/" + ($CloneDir -replace "\\", "/")
}
