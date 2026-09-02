$ErrorActionPreference = "Stop"

$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$runtimeDir = Join-Path $projectRoot ".runtime"
$tryOnScript = Join-Path $PSScriptRoot "start-virtual-tryon.ps1"
$healthUrl = "http://127.0.0.1:7860/health"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

function Wait-ForHealth {
    param([int]$TimeoutSeconds = 180)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3
            if ($health.status -eq "ready") {
                return
            }
        } catch {
            Start-Sleep -Seconds 3
        }
    } while ((Get-Date) -lt $deadline)

    throw "CatVTON khong san sang sau $TimeoutSeconds giay. Xem .runtime/catvton.err.log."
}

$listener = Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue
if (-not $listener) {
    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $tryOnScript) `
        -RedirectStandardOutput (Join-Path $runtimeDir "catvton.out.log") `
        -RedirectStandardError (Join-Path $runtimeDir "catvton.err.log") `
        -WindowStyle Hidden | Out-Null
}

Write-Host "Dang khoi dong CatVTON..."
Wait-ForHealth
Write-Host "CatVTON da san sang tai $healthUrl"

$cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cloudflared) {
    throw "Chua cai cloudflared. Chay: winget install Cloudflare.cloudflared"
}

Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
$tunnelLog = Join-Path $runtimeDir "cloudflared.err.log"
Remove-Item -LiteralPath $tunnelLog -Force -ErrorAction SilentlyContinue

Start-Process `
    -FilePath $cloudflared.Source `
    -ArgumentList @("tunnel", "--url", "http://127.0.0.1:7860", "--no-autoupdate") `
    -RedirectStandardOutput (Join-Path $runtimeDir "cloudflared.out.log") `
    -RedirectStandardError $tunnelLog `
    -WindowStyle Hidden | Out-Null

$deadline = (Get-Date).AddSeconds(60)
do {
    $content = Get-Content -LiteralPath $tunnelLog -Raw -ErrorAction SilentlyContinue
    $match = [regex]::Match([string]$content, "https://[a-z0-9-]+\.trycloudflare\.com")
    if ($match.Success) {
        Write-Host ""
        Write-Host "Virtual Try-On tunnel da san sang:" -ForegroundColor Green
        Write-Host $match.Value -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Dat VIRTUAL_TRYON_INTERNAL_URL tren Vercel bang URL nay va redeploy."
        exit 0
    }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

throw "Khong tao duoc Cloudflare Tunnel. Xem .runtime/cloudflared.err.log."
