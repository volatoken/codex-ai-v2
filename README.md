# Codex AI v2

Hệ thống AI multi-agent điều khiển từ Telegram.

## Kiến trúc

```
Telegram Supergroup
  │
  ├── 📌 Topic cha (control panel)
  │     /agents /model /hire /status ...
  ├── 📐 Architecture (CTO ↔ Critic debate)
  ├── 💻 Code (Engineer implements)
  └── 🧪 Test & Deploy (QA reviews)
  │
  ▼
┌──────────────┐     ┌─────────────────┐
│ Orchestrator │────▶│ CLIProxyAPI     │
│ (Python bot) │     │ :8317           │
│              │     │ ChatGPT OAuth   │
│              │     │ → /v1/chat/...  │
│              │     └─────────────────┘
│              │
│              │────▶┌─────────────────┐
│              │     │ Paperclip       │
│              │     │ :3100           │
│              │     │ Agents / Issues │
└──────────────┘     └─────────────────┘
```

## Thành phần

| Service | Port | Vai trò |
|---------|------|---------|
| CLIProxyAPI | 8317 | Proxy ChatGPT → OpenAI-compatible API |
| Paperclip | 3100 | Control plane — quản lý agents, issues, budget |
| Orchestrator | — | Telegram bot, debate engine, command router |

## Cài đặt (Windows)

### 1. Clone project

```powershell
git clone https://github.com/YOUR_USER/codex-ai-v2.git
cd codex-ai-v2
```

### 2. Chạy installer

```powershell
.\scripts\install.ps1
```

### 3. Cấu hình .env

Mở `.env` và điền:

```
TELEGRAM_BOT_TOKEN=...     # Lấy từ @BotFather
TELEGRAM_GROUP_ID=-100...  # ID supergroup (forum enabled)
TELEGRAM_ADMIN_USER_ID=... # Telegram user ID của bạn
```

### 4. Login ChatGPT vào CLIProxyAPI

```powershell
~\cliproxyapi\CLIProxyAPI.exe --codex-login
```

### 5. Cài Paperclip

```powershell
npx paperclipai onboard --yes
```

### 6. Chạy

```powershell
.\scripts\start.ps1
```

Hoặc chạy từng service riêng:

```powershell
# Terminal 1 — CLIProxyAPI
~\cliproxyapi\CLIProxyAPI.exe --config ~\cliproxyapi\config.yaml

# Terminal 2 — Paperclip
npx paperclipai start

# Terminal 3 — Bot
python -m orchestrator
```

## Lệnh Telegram

Gõ trong **topic cha** của mỗi project:

| Lệnh | Mô tả |
|-------|-------|
| `/idea <mô tả>` | Tạo project mới + bắt đầu debate |
| `/agents` | Xem danh sách agents + model |
| `/model <agent> <model>` | Đổi model cho agent |
| `/hire <slug> "<role>" [model]` | Tạo agent mới |
| `/fire <slug>` | Xóa agent |
| `/pause <slug>` | Tạm dừng agent |
| `/resume <slug>` | Chạy lại agent |
| `/budget <slug> <cents>` | Đặt budget tháng |
| `/status` | Dashboard project |
| `/models` | Xem model khả dụng |
| `/kick <slug>` | Gọi agent chạy ngay |
| `/cost` | Chi phí tháng này |
| `/approve` | Duyệt → chuyển phase tiếp |
| `/reject` | Reject → thiết kế lại |

## Debate CTO ↔ Critic

Khi submit `/idea`, hệ thống tự động:

1. Tạo company + agents trong Paperclip
2. Tạo 4 Telegram topics (parent + arch + code + test)
3. CTO thiết kế kiến trúc (model: o3)
4. Critic phản biện (model: gpt-4o)
5. 2-6 rounds tranh luận, 30s cooldown mỗi round
6. Khi thống nhất → báo user `/approve` hoặc `/reject`

### Quy tắc chống lặp

- Max 6 rounds
- Issues phải giảm qua mỗi round
- ≥80% resolved → auto-agree
- Sau 4 rounds + >2 open issues → escalate to user
- 30s cooldown giữa mỗi round

## Cấu trúc thư mục

```
codex-ai-v2/
├── .env.example            # Template cấu hình
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container build
├── docker-compose.yml      # Optional Docker setup
├── cliproxyapi/
│   └── config.yaml         # CLIProxyAPI config
├── orchestrator/
│   ├── main.py             # Entry point
│   ├── config.py           # Env vars
│   ├── llm.py              # CLIProxyAPI client
│   ├── paperclip.py        # Paperclip API client
│   ├── telegram_bot.py     # Telegram bot + handlers
│   ├── topic_manager.py    # Topic auto-creation
│   ├── debate.py           # CTO ↔ Critic state machine
│   ├── commands.py         # /agents /model /hire etc.
│   ├── agents.py           # Agent definitions + prompts
│   └── kv.py               # JSON KV store
├── scripts/
│   ├── install.ps1         # Windows installer
│   └── start.ps1           # Start all services
└── data/
    └── kv.json             # Runtime state (gitignored)
```

## License

MIT
