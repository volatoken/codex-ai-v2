# Codex AI v2

Hệ thống AI multi-agent điều khiển từ Telegram.
**Option B Architecture**: OpenFang = agent execution, Paperclip = project management.

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
│ Orchestrator │────▶│ OpenFang        │
│ (Python bot) │     │ :4200           │
│              │     │ Agent execution │
│  - Topics    │     │ 76 REST APIs    │
│  - Debate    │     │ TOML manifests  │
│  - Commands  │     └───────┬─────────┘
│              │             │
│              │     ┌───────▼─────────┐
│              │     │ CLIProxyAPI     │
│              │     │ :8317           │
│              │     │ ChatGPT proxy   │
│              │     └─────────────────┘
│              │
│              │────▶┌─────────────────┐
│              │     │ Paperclip       │
│              │     │ :3100           │
│              │     │ Project mgmt    │
└──────────────┘     └─────────────────┘
```

## Thành phần

| Service | Port | Vai trò |
|---------|------|---------|
| OpenFang | 4200 | Agent execution engine — spawn, LLM calls, models, memory, security |
| CLIProxyAPI | 8317 | Proxy ChatGPT OAuth → OpenAI-compatible API (OpenFang provider) |
| Paperclip | 3100 | Project management — company, goals, issues, budget tracking |
| Orchestrator | — | Telegram bot, debate engine, sync layer |

## Cài đặt (Windows)

### 1. Clone project

```powershell
git clone https://github.com/volatoken/codex-ai-v2.git
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
OPENFANG_API_KEY=...       # OpenFang API key (optional)
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
# Terminal 1 — OpenFang
~\openfang\openfang.exe --config ~\openfang\config.toml

# Terminal 2 — CLIProxyAPI
~\cliproxyapi\CLIProxyAPI.exe --config ~\cliproxyapi\config.yaml

# Terminal 3 — Paperclip
npx paperclipai start

# Terminal 4 — Bot
python -m orchestrator
```

## Lệnh Telegram

Gõ trong **topic cha** của mỗi project:

| Lệnh | Mô tả |
|-------|-------|
| `/idea <mô tả>` | Tạo project mới + bắt đầu debate |
| `/agents` | Xem danh sách agents (từ OpenFang) |
| `/model <agent> <model>` | Đổi model cho agent (OpenFang) |
| `/hire <slug> "<role>" [model]` | Tạo agent (OpenFang + Paperclip) |
| `/fire <slug>` | Xóa agent (cả 2 hệ thống) |
| `/pause <slug>` | Tạm dừng agent (OpenFang stop) |
| `/resume <slug>` | Chạy lại agent (OpenFang reset) |
| `/budget <slug> <cents>` | Đặt budget tháng (Paperclip) |
| `/status` | Dashboard: OF agents + Paperclip tasks |
| `/models` | Xem 51+ models khả dụng (OpenFang) |
| `/kick <slug>` | Gửi wake message cho agent |
| `/cost` | Chi phí token tháng này (OpenFang) |
| `/approve` | Duyệt → chuyển phase tiếp |
| `/reject` | Reject → thiết kế lại |

## Debate CTO ↔ Critic

Khi submit `/idea`, hệ thống tự động:

1. Tạo company + agents trong Paperclip (budget tracking)
2. Spawn CTO + Critic agents trong OpenFang (execution)
3. Tạo 4 Telegram topics (parent + arch + code + test)
4. CTO thiết kế kiến trúc via OpenFang agent (model: o3)
5. Critic phản biện via OpenFang agent (model: gpt-4o)
6. 2-6 rounds tranh luận, 30s cooldown mỗi round
7. Khi thống nhất → báo user `/approve` hoặc `/reject`

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
├── docker-compose.yml      # Docker setup (4 services)
├── openfang/
│   └── config.toml         # OpenFang config (CLIProxyAPI as provider)
├── cliproxyapi/
│   └── config.yaml         # CLIProxyAPI config
├── orchestrator/
│   ├── main.py             # Entry point
│   ├── config.py           # Env vars
│   ├── openfang.py         # OpenFang REST API client
│   ├── paperclip.py        # Paperclip API client
│   ├── telegram_bot.py     # Telegram bot + handlers
│   ├── topic_manager.py    # Topic auto-creation
│   ├── debate.py           # CTO ↔ Critic state machine
│   ├── commands.py         # /agents /model /hire etc.
│   ├── agents.py           # Agent definitions, prompts, TOML builder
│   └── kv.py               # JSON KV store (orchestrator state)
├── scripts/
│   ├── install.ps1         # Windows installer
│   └── start.ps1           # Start all services
└── data/
    └── kv.json             # Runtime state (gitignored)
```

## License

MIT
