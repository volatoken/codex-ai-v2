# ============================================================
# start.ps1 — Khởi động tất cả services
# ============================================================
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host 'Codex AI v2 — Starting services...' -ForegroundColor Cyan

# ── 1. OpenFang ──────────────────────────────────────────────
Write-Host '[1/4] OpenFang...' -ForegroundColor Yellow
$openfangExe = Join-Path $HOME 'openfang' 'openfang.exe'
$openfangConfig = Join-Path $HOME 'openfang' 'config.toml'

if (Test-Path $openfangExe) {
    Start-Process -FilePath $openfangExe `
        -ArgumentList "--config", $openfangConfig `
        -WindowStyle Minimized
    Write-Host '  OpenFang started (port 4200)' -ForegroundColor Green
} else {
    Write-Host '  openfang.exe không tìm thấy! Chạy install.ps1 trước.' -ForegroundColor Red
}

# ── 2. CLIProxyAPI ───────────────────────────────────────────
Write-Host '[2/4] CLIProxyAPI...' -ForegroundColor Yellow
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

# ── 3. Paperclip ─────────────────────────────────────────────
Write-Host '[3/4] Paperclip...' -ForegroundColor Yellow
Start-Process -FilePath 'npx' `
    -ArgumentList 'paperclipai', 'start' `
    -WindowStyle Minimized
Write-Host '  Paperclip started (port 3100)' -ForegroundColor Green

# Wait for services
Write-Host '  Đợi 5s cho services khởi động...' -ForegroundColor DarkYellow
Start-Sleep -Seconds 5

# ── 4. Orchestrator ──────────────────────────────────────────
Write-Host '[4/4] Orchestrator bot...' -ForegroundColor Yellow
Push-Location $projectDir
python -m orchestrator
Pop-Location
