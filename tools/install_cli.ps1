$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$toolDir = Join-Path $projectRoot '.tools'
New-Item -ItemType Directory -Force -Path $toolDir | Out-Null
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/databricks/cli/releases/latest'
# Use the release archive so the CLI stays local to this project.
$asset = $release.assets | Where-Object { $_.name -match '^databricks_cli_.*_windows_amd64\.zip$' } | Select-Object -First 1
if (-not $asset) { throw 'Official release has no Windows AMD64 zip asset' }
$checksumAsset = $release.assets | Where-Object { $_.name -match '_SHA256SUMS$' } | Select-Object -First 1
if (-not $checksumAsset) { throw 'Official release has no checksum manifest' }
$archive = Join-Path $toolDir $asset.name
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archive
$checksums = (Invoke-WebRequest -Uri $checksumAsset.browser_download_url).Content
if ($checksums -is [byte[]]) { $checksums = [System.Text.Encoding]::UTF8.GetString($checksums) }
$matchingLine = ($checksums -split "`n") | Where-Object { $_.Trim().EndsWith($asset.name) } | Select-Object -First 1
if (-not $matchingLine) { throw 'Missing archive checksum' }
$expected = ($matchingLine.Trim() -split '\s+')[0]
$actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
# Check the downloaded archive before extracting or running it.
if ($actual -ne $expected) { throw 'Databricks CLI checksum mismatch' }
Expand-Archive -LiteralPath $archive -DestinationPath $toolDir -Force
& (Join-Path $toolDir 'databricks.exe') version
