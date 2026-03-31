# ============================================================
# start.ps1 — Khởi động tất cả services
# ============================================================
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host 'Codex AI v2 — Starting services...' -ForegroundColor Cyan

# ── 1. CLIProxyAPI ───────────────────────────────────────────
Write-Host '[1/3] CLIProxyAPI...' -ForegroundColor Yellow
$cliproxyExe = Join-Path $HOME 'cliproxyapi' 'CLIProxyAPI.exe'
$cliproxyConfig = Join-Path $HOME 'cliproxyapi' 'config.yaml'

if (Test-Path $cliproxyExe) {
    Start-Process -FilePath $cliproxyExe `
        -ArgumentList "--config", $cliproxyConfig `
        -WindowStyle Minimized
    Write-Host '  CLIProxyAPI started (port 8317)' -ForegroundColor Green
} else {
    Write-Host '  CLIProxyAPI.exe không tìm thấy! Chạy install.ps1 trước.' -ForegroundColor Red
}

# ── 2. Paperclip ─────────────────────────────────────────────
Write-Host '[2/3] Paperclip...' -ForegroundColor Yellow
Start-Process -FilePath 'npx' `
    -ArgumentList 'paperclipai', 'start' `
    -WindowStyle Minimized
Write-Host '  Paperclip started (port 3100)' -ForegroundColor Green

# Wait for services
Write-Host '  Đợi 5s cho services khởi động...' -ForegroundColor DarkYellow
Start-Sleep -Seconds 5

# ── 3. Orchestrator ──────────────────────────────────────────
Write-Host '[3/3] Orchestrator bot...' -ForegroundColor Yellow
Push-Location $projectDir
python -m orchestrator
Pop-Location
