[CmdletBinding()]
param(
    [string]$HostIp,
    [int]$FrontendPort = 3000,
    [int]$BackendPort = 8010,
    [int]$DatabasePort = 5433
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$mobileDir = Join-Path $repoRoot "mobile"
$pythonCandidates = @(
    (Join-Path $repoRoot ".venv\Scripts\python.exe"),
    (Join-Path $backendDir ".venv\Scripts\python.exe")
)
$pythonPath = $pythonCandidates | Where-Object {
    Test-Path -LiteralPath $_ -PathType Leaf
} | Select-Object -First 1

function Resolve-LanAddress {
    param([string]$ExplicitAddress)

    if ($ExplicitAddress) {
        $parsed = [System.Net.IPAddress]::Parse($ExplicitAddress)
        if ($parsed.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
            throw "HostIp phải là địa chỉ IPv4 trong LAN."
        }
        return $parsed.ToString()
    }

    $socket = [System.Net.Sockets.UdpClient]::new()
    try {
        # Connect only selects the interface used by the default route; no
        # packet or application data is sent.
        $socket.Connect("8.8.8.8", 65530)
        return ([System.Net.IPEndPoint]$socket.Client.LocalEndPoint).Address.ToString()
    }
    finally {
        $socket.Dispose()
    }
}

function Assert-Directory {
    param([string]$Path, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "Không tìm thấy $Label tại $Path"
    }
}

Assert-Directory $backendDir "backend"
Assert-Directory $frontendDir "frontend"
Assert-Directory $mobileDir "mobile"
if (-not $pythonPath) {
    throw "Không tìm thấy Python venv ở repo root hoặc backend/.venv. Hãy cài backend dependencies trước."
}
if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules") -PathType Container)) {
    throw "Frontend chưa có node_modules. Chạy npm install trong frontend trước."
}
if (-not (Test-Path -LiteralPath (Join-Path $mobileDir "node_modules") -PathType Container)) {
    throw "Mobile chưa có node_modules. Chạy npm install trong mobile trước."
}

$lanAddress = Resolve-LanAddress $HostIp
$webUrl = "http://${lanAddress}:$FrontendPort"
$backendUrl = "http://127.0.0.1:$BackendPort"

# Start and validate the project-owned database before any backend process can
# accidentally connect to another PostgreSQL instance on this machine.
& (Join-Path $PSScriptRoot "start-area303-db.ps1") -Port $DatabasePort
if ($LASTEXITCODE -ne 0) { throw "AREA-303 database startup failed." }

$env:AREA303_DEBUG = "false"
$env:POSTGRES_HOST = "127.0.0.1"
$env:POSTGRES_PORT = "$DatabasePort"
Push-Location $backendDir
try {
    & $pythonPath -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "AREA-303 database migration failed." }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "AREA 303 local mobile" -ForegroundColor Magenta
Write-Host "Web trên iPhone : $webUrl" -ForegroundColor Cyan
Write-Host "Backend nội bộ  : $backendUrl" -ForegroundColor DarkCyan
Write-Host "AREA database   : 127.0.0.1:$DatabasePort (không dùng Tekno :5432)" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "Ba terminal sẽ mở. Giữ chúng chạy và quét QR trong terminal Expo bằng Expo Go." -ForegroundColor Yellow

$backendCommand = @"
Set-Location -LiteralPath '$backendDir'
`$env:DEBUG = 'false'
`$env:POSTGRES_HOST = '127.0.0.1'
`$env:POSTGRES_PORT = '$DatabasePort'
& '$pythonPath' -m uvicorn app.main:app --reload --host 127.0.0.1 --port $BackendPort
"@

$frontendCommand = @"
Set-Location -LiteralPath '$frontendDir'
`$env:NEXT_PUBLIC_API_URL = '/api/v1'
`$env:BACKEND_INTERNAL_URL = '$backendUrl'
npm run dev:lan -- -p $FrontendPort
"@

$mobileCommand = @"
Set-Location -LiteralPath '$mobileDir'
`$env:EXPO_PUBLIC_WEB_URL = '$webUrl'
npm run start:lan
"@

# These windows are intentionally visible: the developer needs the server logs,
# Expo QR code and Ctrl+C controls while testing on a physical phone.
Start-Process powershell.exe -WindowStyle Normal -ArgumentList @("-NoExit", "-Command", $backendCommand)
Start-Process powershell.exe -WindowStyle Normal -ArgumentList @("-NoExit", "-Command", $frontendCommand)
Start-Process powershell.exe -WindowStyle Normal -ArgumentList @("-NoExit", "-Command", $mobileCommand)

Write-Host "Đã khởi động. Nếu Windows Firewall hỏi, chỉ cho phép Node.js trên Private networks." -ForegroundColor Green
