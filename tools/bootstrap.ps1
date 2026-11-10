param(
    [string]$Profile = 'RETAIL_DEMO',
    [string]$Catalog = 'retail_demo',
    [string]$WarehouseId = ''
)
$ErrorActionPreference = 'Stop'
if ($Catalog -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') { throw 'Invalid catalog identifier' }
$projectRoot = Split-Path -Parent $PSScriptRoot
$localCli = Join-Path $projectRoot '.tools/databricks.exe'
$cli = if (Test-Path -LiteralPath $localCli) { $localCli } else { 'databricks' }
if (-not $WarehouseId) {
    $warehouses = (& $cli warehouses list -p $Profile -o json) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot list SQL warehouses; authenticate first' }
    $WarehouseId = ($warehouses | Select-Object -First 1).id
}
if (-not $WarehouseId) { throw 'Use the existing serverless SQL warehouse ID' }
$cacheDir = Join-Path $projectRoot '.cache'
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
$bodyPath = Join-Path $cacheDir 'bootstrap-statement.json'
$statements = @("CREATE CATALOG IF NOT EXISTS $Catalog")
foreach ($schema in @('raw_share', 'bronze', 'silver', 'gold')) {
    $statements += "CREATE SCHEMA IF NOT EXISTS $Catalog.$schema"
}
foreach ($sql in $statements) {
    $body = @{warehouse_id=$WarehouseId; statement=$sql; wait_timeout='50s'; on_wait_timeout='CONTINUE'}
    $body | ConvertTo-Json | Set-Content -LiteralPath $bodyPath -Encoding utf8
    $response = (& $cli api post /api/2.0/sql/statements --json "@$bodyPath" -p $Profile -o json) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "SQL request failed: $sql" }
    $deadline = [DateTime]::UtcNow.AddMinutes(5)
    while ($response.status.state -in @('PENDING','RUNNING')) {
        if ([DateTime]::UtcNow -ge $deadline) { throw "SQL timed out; inspect statement $($response.statement_id)" }
        Start-Sleep -Seconds 2
        $response = (& $cli api get "/api/2.0/sql/statements/$($response.statement_id)" -p $Profile -o json) | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) { throw 'Cannot read SQL statement status' }
    }
    if ($response.status.state -ne 'SUCCEEDED') {
        throw ($response.status | ConvertTo-Json -Depth 10)
    }
    Write-Output "Ready: $sql"
}
