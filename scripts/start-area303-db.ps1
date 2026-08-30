[CmdletBinding()]
param(
    [int]$Port = 5433
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$dataDir = Join-Path $repoRoot "backend\var\area303-postgres"
$logPath = Join-Path $repoRoot "backend\var\area303-postgres.log"
$pgBin = "C:\Program Files\PostgreSQL\18\bin"
$initDb = Join-Path $pgBin "initdb.exe"
$pgCtl = Join-Path $pgBin "pg_ctl.exe"
$pgReady = Join-Path $pgBin "pg_isready.exe"
$createdb = Join-Path $pgBin "createdb.exe"
$psql = Join-Path $pgBin "psql.exe"

foreach ($binary in @($initDb, $pgCtl, $pgReady, $createdb, $psql)) {
    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
        throw "Thiếu PostgreSQL binary: $binary"
    }
}

$portOwner = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($portOwner) {
    & $pgReady -h 127.0.0.1 -p $Port -d area303 -U area303 *> $null
    if ($LASTEXITCODE -eq 0) {
        $actualDataDir = (& $psql -h 127.0.0.1 -p $Port -U area303 -d area303 -tAc "SHOW data_directory").Trim()
        $expectedDataDir = [System.IO.Path]::GetFullPath($dataDir).TrimEnd('\')
        $actualFullPath = [System.IO.Path]::GetFullPath($actualDataDir).TrimEnd('\')
        if ($actualFullPath -ne $expectedDataDir) {
            throw "Port $Port có PostgreSQL nhưng data directory không thuộc AREA-303: $actualDataDir"
        }
        Write-Host "AREA-303 PostgreSQL đã chạy tại 127.0.0.1:$Port" -ForegroundColor Green
        exit 0
    }
    throw "Port $Port đang do process khác sử dụng. Không khởi động để tránh kết nối nhầm database."
}

if (-not (Test-Path -LiteralPath (Join-Path $dataDir "PG_VERSION") -PathType Leaf)) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $dataDir) -Force | Out-Null
    Write-Host "Khởi tạo PostgreSQL cluster riêng cho AREA-303 tại $dataDir" -ForegroundColor Cyan
    # Trust is restricted by the server flags below to loopback-only local
    # development. This cluster is never exposed to Wi-Fi or the internet.
    & $initDb -D $dataDir -U area303 --encoding=UTF8 --auth-local=trust --auth-host=trust
    if ($LASTEXITCODE -ne 0) { throw "initdb thất bại." }
}

& $pgCtl -D $dataDir -l $logPath -o "-p $Port -h 127.0.0.1" start
if ($LASTEXITCODE -ne 0) { throw "Không thể khởi động PostgreSQL AREA-303." }

for ($attempt = 0; $attempt -lt 20; $attempt++) {
    & $pgReady -h 127.0.0.1 -p $Port -d postgres -U area303 *> $null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Milliseconds 250
}
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL AREA-303 không ready tại port $Port." }

$exists = & $psql -h 127.0.0.1 -p $Port -U area303 -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='area303'"
if ($exists -ne "1") {
    & $createdb -h 127.0.0.1 -p $Port -U area303 area303
    if ($LASTEXITCODE -ne 0) { throw "Không thể tạo database area303." }
}

Write-Host "AREA-303 PostgreSQL sẵn sàng tại 127.0.0.1:$Port" -ForegroundColor Green
Write-Host "Tekno tại port 5432 không bị truy cập hoặc thay đổi." -ForegroundColor DarkGray
