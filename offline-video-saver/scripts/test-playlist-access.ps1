[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PlaylistUrl,

    [ValidateRange(10, 300)]
    [int]$Seconds = 60
)

$ErrorActionPreference = "Stop"
$image = "cr20kb-offline-video-saver:host-access-test"
$projectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$testDir = Join-Path $projectDir ".local-access-test"

Write-Host "Testing anonymous YouTube media access from this computer."
Write-Host "Only the first $Seconds seconds of the first playlist item will be fetched."

try {
    if (Test-Path $testDir) {
        Remove-Item -Recurse -Force $testDir
    }
    New-Item -ItemType Directory -Path $testDir | Out-Null

    Push-Location $projectDir
    try {
        & docker build -t $image .
        if ($LASTEXITCODE -ne 0) {
            throw "Docker image build failed."
        }

        $section = "*0-$Seconds"
        $mount = "type=bind,source=$testDir,target=/test"
        & docker run --rm `
            --mount $mount `
            --entrypoint /usr/local/bin/yt-dlp-cr20kb `
            $image `
            --ignore-config `
            --playlist-items 1 `
            --download-sections $section `
            --force-keyframes-at-cuts `
            --no-warnings `
            --js-runtimes node `
            --format "bv*[height<=480]+ba/b[height<=480]/b" `
            --merge-output-format mkv `
            --paths /test `
            --output "%(id)s.%(ext)s" `
            --print "after_move:filepath" `
            $PlaylistUrl

        if ($LASTEXITCODE -ne 0) {
            throw "YouTube rejected media access from this host or yt-dlp failed."
        }
    }
    finally {
        Pop-Location
    }

    $result = Get-ChildItem -File $testDir | Sort-Object Length -Descending | Select-Object -First 1
    if (-not $result -or $result.Length -le 0) {
        throw "The command exited without a non-empty media sample."
    }

    $megabytes = [math]::Round($result.Length / 1MB, 2)
    Write-Host "SUCCESS: media access works from this host."
    Write-Host "Temporary sample: $($result.Name), $megabytes MB"
}
finally {
    if (Test-Path $testDir) {
        Remove-Item -Recurse -Force $testDir
    }
}
