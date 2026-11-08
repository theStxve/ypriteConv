# Puts ffmpeg.exe + ffprobe.exe into .\bin for bundling.
# Uses a local FFmpeg from PATH if available, otherwise downloads the
# "essentials" release build from gyan.dev (GPL, includes libx264).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$bin = Join-Path $root 'bin'
New-Item -ItemType Directory -Force -Path $bin | Out-Null

$local = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
if ($local -and -not $env:CI) {
    $dir = Split-Path -Parent $local.Source
    Copy-Item $local.Source (Join-Path $bin 'ffmpeg.exe') -Force
    $probe = Join-Path $dir 'ffprobe.exe'
    if (Test-Path $probe) { Copy-Item $probe (Join-Path $bin 'ffprobe.exe') -Force }
    Write-Host "[INFO] Copied FFmpeg from $dir"
    exit 0
}

$url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("ffmpeg-" + [guid]::NewGuid())
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$zip = Join-Path $tmp 'ffmpeg.zip'
Write-Host "[INFO] Downloading $url"
Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
Expand-Archive -Path $zip -DestinationPath $tmp -Force
foreach ($exe in 'ffmpeg.exe', 'ffprobe.exe') {
    $found = Get-ChildItem -Path $tmp -Recurse -Filter $exe | Select-Object -First 1
    if (-not $found) { throw "$exe not found in archive" }
    Copy-Item $found.FullName (Join-Path $bin $exe) -Force
}
Remove-Item -Recurse -Force $tmp
Write-Host "[INFO] FFmpeg ready in $bin"
