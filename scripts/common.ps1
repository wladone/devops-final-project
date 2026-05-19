function Get-ProjectPython {
    $candidates = @(
        $env:PROJECT_PYTHON,
        "python",
        "py -3",
        "C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin\python.exe"
    ) | Where-Object { $_ -and $_.Trim().Length -gt 0 }

    foreach ($candidate in $candidates) {
        try {
            if ($candidate -match "\.exe$") {
                if (Test-Path $candidate) {
                    return $candidate
                }
            }
            else {
                $null = Invoke-Expression "$candidate --version" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    return $candidate
                }
            }
        }
        catch {
        }
    }

    return $null
}

function Get-VenvPython {
    param (
        [string]$ProjectRoot = $PWD
    )

    $candidates = @(
        (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
        (Join-Path $ProjectRoot ".venv\bin\python")
    )

    foreach ($candidate in $candidates) {
        if (-not (Test-Path $candidate)) {
            continue
        }

        try {
            & $candidate --version | Out-Null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        }
        catch {
        }
    }

    return $null
}

function Add-ProjectBinToPath {
    $projectBin = Join-Path $HOME "bin"
    if (-not (Test-Path $projectBin)) {
        return
    }

    $pathEntries = $env:Path -split ';' | Where-Object { $_ }
    if ($pathEntries -contains $projectBin) {
        return
    }

    $env:Path = "$projectBin;$env:Path"
}
