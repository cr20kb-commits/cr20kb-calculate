[CmdletBinding()]
param(
    [string]$OutputDir,
    [string]$PackageName = "CR20KB-VideoSaver-Windows-x64"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectDir = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $OutputDir) {
    $OutputDir = Join-Path $projectDir "dist"
}
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)

$pythonVersion = "3.13.15"
$pythonArchiveName = "python-$pythonVersion-embed-amd64.zip"
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/$pythonArchiveName"
$pythonSha256 = "d1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf"

$packageDir = Join-Path $OutputDir $PackageName
$runtimeDir = Join-Path $packageDir "runtime"
$sitePackages = Join-Path $runtimeDir "Lib\site-packages"
$zipPath = Join-Path $OutputDir "$PackageName.zip"
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cr20kb-portable-" + [guid]::NewGuid().ToString("N"))
$pythonArchive = Join-Path $tempDir $pythonArchiveName

function Assert-LastExitCode([string]$Action) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Action failed with exit code $LASTEXITCODE."
    }
}

try {
    Remove-Item -Recurse -Force $packageDir -ErrorAction SilentlyContinue
    Remove-Item -Force $zipPath -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

    Write-Host "Downloading official Python $pythonVersion embeddable runtime..."
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonArchive
    $actualHash = (Get-FileHash -Path $pythonArchive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $pythonSha256) {
        throw "Python archive SHA-256 mismatch. Expected $pythonSha256, got $actualHash."
    }
    Expand-Archive -Path $pythonArchive -DestinationPath $runtimeDir -Force

    $pthFile = Get-ChildItem -Path $runtimeDir -Filter "python*._pth" | Select-Object -First 1
    if (-not $pthFile) {
        throw "Python embeddable _pth file was not found."
    }
    @(
        "python313.zip",
        ".",
        "Lib\site-packages",
        "import site"
    ) | Set-Content -Path $pthFile.FullName -Encoding Ascii

    New-Item -ItemType Directory -Path $sitePackages -Force | Out-Null
    Write-Host "Installing pinned web runtime dependencies..."
    & python -m pip install `
        --disable-pip-version-check `
        --no-compile `
        --only-binary=:all: `
        --target $sitePackages `
        -r (Join-Path $PSScriptRoot "runtime-requirements.txt")
    Assert-LastExitCode "Portable dependency installation"

    Copy-Item -Path (Join-Path $projectDir "app") -Destination (Join-Path $runtimeDir "app") -Recurse -Force
    Copy-Item -Path (Join-Path $PSScriptRoot "launcher.py") -Destination (Join-Path $runtimeDir "launcher.py") -Force
    Copy-Item -Path (Join-Path $PSScriptRoot "package\*") -Destination $packageDir -Recurse -Force
    Copy-Item -Path (Join-Path $projectDir "LICENSE") -Destination (Join-Path $packageDir "LICENSE.txt") -Force
    Copy-Item -Path (Join-Path $projectDir "THIRD_PARTY_NOTICES.md") -Destination $packageDir -Force
    Copy-Item -Path (Join-Path $projectDir "PROJECT_STATUS.md") -Destination $packageDir -Force

    foreach ($directoryName in @("tools", "data", "config", "logs")) {
        $directory = Join-Path $packageDir $directoryName
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
        "Created by the portable launcher." | Set-Content -Path (Join-Path $directory ".keep.txt") -Encoding UTF8
    }

    $versionText = @(
        "CR20KB Offline Video Saver Windows portable preview",
        "Built: $([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))",
        "Commit: $($env:GITHUB_SHA ?? 'local-build')",
        "Python: $pythonVersion"
    )
    $versionText | Set-Content -Path (Join-Path $packageDir "PORTABLE_VERSION.txt") -Encoding UTF8

    Get-ChildItem -Path $packageDir -Directory -Recurse -Filter "__pycache__" |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $packageDir -File -Recurse -Include "*.pyc", "*.pyo" |
        Remove-Item -Force -ErrorAction SilentlyContinue

    Push-Location $runtimeDir
    try {
        $env:DATA_DIR = Join-Path $packageDir "data"
        & (Join-Path $runtimeDir "python.exe") -c "import fastapi, uvicorn, app.main; print('portable imports: OK')"
        Assert-LastExitCode "Embedded Python import smoke test"
        & (Join-Path $runtimeDir "python.exe") (Join-Path $runtimeDir "launcher.py") --self-test
        Assert-LastExitCode "Portable launcher self-test"
    }
    finally {
        Pop-Location
    }

    Write-Host "Creating $zipPath ..."
    Compress-Archive -Path $packageDir -DestinationPath $zipPath -CompressionLevel Optimal -Force
    if (-not (Test-Path $zipPath) -or (Get-Item $zipPath).Length -le 0) {
        throw "Portable ZIP was not created."
    }

    $zipHash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    "$zipHash  $([System.IO.Path]::GetFileName($zipPath))" |
        Set-Content -Path (Join-Path $OutputDir "$PackageName.sha256") -Encoding Ascii

    Write-Host "Portable package ready: $zipPath"
}
finally {
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
}
