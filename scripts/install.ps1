# ============================================================
# install.ps1 — Cài đặt Codex AI v2 trên Windows
# ============================================================
$ErrorActionPreference = 'Stop'

Write-Host '============================================' -ForegroundColor Cyan
Write-Host '  Codex AI v2 — Installer                  ' -ForegroundColor Cyan
Write-Host '  Paperclip + CLIProxyAPI + Telegram Bot    ' -ForegroundColor Cyan
Write-Host '============================================' -ForegroundColor Cyan
Write-Host ''

# ── 1. Check Python ─────────────────────────────────────────
Write-Host '[1/5] Kiểm tra Python...' -ForegroundColor Yellow
try {
    $pyVer = python --version 2>&1
    Write-Host "  $pyVer" -ForegroundColor Green
} catch {
    Write-Host '  Python chưa cài! Tải tại https://python.org/downloads' -ForegroundColor Red
    exit 1
}

# ── 2. Check Node.js ────────────────────────────────────────
Write-Host '[2/5] Kiểm tra Node.js...' -ForegroundColor Yellow
try {
    $nodeVer = node --version 2>&1
    Write-Host "  Node.js $nodeVer" -ForegroundColor Green
} catch {
    Write-Host '  Node.js chưa cài! Tải tại https://nodejs.org' -ForegroundColor Red
    exit 1
}

# ── 3. Install Python dependencies ──────────────────────────
Write-Host '[3/5] Cài Python dependencies...' -ForegroundColor Yellow
$projectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Push-Location $projectDir
pip install -r requirements.txt
Pop-Location
Write-Host '  Dependencies đã cài.' -ForegroundColor Green

# ── 4. Setup CLIProxyAPI ────────────────────────────────────
Write-Host '[4/5] Setup CLIProxyAPI...' -ForegroundColor Yellow
$cliproxyDir = Join-Path $HOME 'cliproxyapi'
$cliproxyExe = Join-Path $cliproxyDir 'CLIProxyAPI.exe'

if (!(Test-Path $cliproxyExe)) {
    Write-Host '  Tải CLIProxyAPI từ GitHub...' -ForegroundColor DarkYellow
    New-Item -ItemType Directory -Force -Path $cliproxyDir | Out-Null

    try {
        $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/router-for-me/CLIProxyAPI/releases/latest'
        $asset = $release.assets | Where-Object {
            $_.name -like '*windows*amd64*' -or $_.name -like '*Windows*x86_64*'
        } | Select-Object -First 1

        if ($asset) {
            $zipFile = Join-Path $env:TEMP 'cliproxyapi.zip'
            Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipFile
            Expand-Archive -Path $zipFile -DestinationPath $cliproxyDir -Force
            Remove-Item $zipFile -Force -ErrorAction SilentlyContinue

            $exe = Get-ChildItem -Path $cliproxyDir -Recurse -Filter '*.exe' | Select-Object -First 1
            if ($exe -and ($exe.FullName -ne $cliproxyExe)) {
                Move-Item -Path $exe.FullName -Destination $cliproxyExe -Force
            }
            Write-Host "  CLIProxyAPI: $cliproxyExe" -ForegroundColor Green
        } else {
            Write-Host '  Không tìm thấy asset Windows.' -ForegroundColor Red
            Write-Host '  Tải thủ công: https://github.com/router-for-me/CLIProxyAPI/releases' -ForegroundColor White
        }
    } catch {
        Write-Host "  Lỗi tải CLIProxyAPI: $_" -ForegroundColor Red
    }
} else {
    Write-Host "  CLIProxyAPI đã có: $cliproxyExe" -ForegroundColor Green
}

# Copy config
$cliproxyConfig = Join-Path $cliproxyDir 'config.yaml'
$sourceConfig = Join-Path $projectDir 'cliproxyapi' 'config.yaml'
if (!(Test-Path $cliproxyConfig) -and (Test-Path $sourceConfig)) {
    Copy-Item $sourceConfig $cliproxyConfig
    Write-Host '  Config đã copy vào cliproxyapi/' -ForegroundColor Green
}

# ── 5. Setup .env ────────────────────────────────────────────
Write-Host '[5/5] Setup .env...' -ForegroundColor Yellow
Push-Location $projectDir

if (!(Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host '  .env đã tạo từ .env.example' -ForegroundColor Green
    Write-Host '  → Mở .env và điền TELEGRAM_BOT_TOKEN, GROUP_ID, ADMIN_USER_ID' -ForegroundColor DarkYellow
} else {
    Write-Host '  .env đã tồn tại.' -ForegroundColor Green
}

# Create data dir
New-Item -ItemType Directory -Force -Path data | Out-Null

Pop-Location

Write-Host ''
Write-Host '============================================' -ForegroundColor Green
Write-Host '  Cài đặt xong!                            ' -ForegroundColor Green
Write-Host '============================================' -ForegroundColor Green
Write-Host ''
Write-Host 'Bước tiếp theo:' -ForegroundColor Cyan
Write-Host '  1. Sửa .env → điền Telegram token + IDs' -ForegroundColor White
Write-Host '  2. Login ChatGPT:' -ForegroundColor White
Write-Host "     $cliproxyExe --codex-login" -ForegroundColor White
Write-Host '  3. Chạy CLIProxyAPI:' -ForegroundColor White
Write-Host "     $cliproxyExe --config $cliproxyConfig" -ForegroundColor White
Write-Host '  4. Cài Paperclip:' -ForegroundColor White
Write-Host '     npx paperclipai onboard --yes' -ForegroundColor White
Write-Host '  5. Chạy bot:' -ForegroundColor White
Write-Host '     python -m orchestrator' -ForegroundColor White
