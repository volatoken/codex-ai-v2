# Codex AI v2

Hệ thống AI multi-agent điều khiển từ Telegram.
**Cross-system debate**: Paperclip CTO (backbone) ↔ OpenFang Critic (reviewer).

## Kiến trúc

```
Telegram Supergroup
  │
  ├── 📌 Topic cha (control panel)
  ├── 📐 Architecture (CTO ↔ Critic debate)
  ├── 💻 Code (Engineer implements)
  └── 🧪 Test & Deploy (QA reviews)
  │
  ▼
┌──────────────────┐
│   Orchestrator   │ (Python bot — referee)
│   - Topics       │
│   - Debate       │
│   - Commands     │
└──┬───────────┬───┘
   │           │
   ▼           ▼
┌──────────┐  ┌──────────────┐
│Paperclip │  │  OpenFang    │
│:3100     │  │  :4200       │
│ BACKBONE │  │  REVIEWER    │
│          │  │              │
│ CTO ─────┤  │  Critic ─────┤
│ Engineer │  │  (phản biện  │
│ QA       │  │   tối ưu)    │
│          │  │              │
│ adapter──┤  │  provider────┤
└────┬─────┘  └──────┬───────┘
     │               │
     ▼               ▼
┌────────────────────────────┐
│       CLIProxyAPI :8317    │
│    ChatGPT OAuth proxy     │
│    /v1/chat/completions    │
└────────────────────────────┘
```

## Phân hệ

| Service | Port | Vai trò | Agents |
|---------|------|---------|--------|
| **Paperclip** | 3100 | **Backbone** — thiết kế, code, test, budget, issues | CTO, Engineer, QA |
| **OpenFang** | 4200 | **Reviewer** — phản biện, security, tối ưu kiến trúc | Critic |
| CLIProxyAPI | 8317 | Proxy ChatGPT → OpenAI-compatible API | — |
| Orchestrator | — | Telegram bot, debate referee, sync layer | — |

### Debate CTO ↔ Critic (cross-system)

```
Idea → Orchestrator
         │
    ┌────▼────┐        ┌────────────┐
    │Paperclip│ design  │  OpenFang  │
    │  CTO    │────────▶│   Critic   │
    │ (o3)    │◀────────│  (gpt-4o)  │
    │         │ review  │            │
    └─────────┘        └────────────┘
         │
    2-6 rounds → agree → /approve → Engineer code → QA test
```

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
| `/agents` | Xem agents từ cả Paperclip (PC) và OpenFang (OF) |
| `/model <agent> <model>` | Đổi model (auto detect PC/OF) |
| `/hire <slug> "<role>" [model]` | Tạo agent — critic→OF, còn lại→PC |
| `/fire <slug>` | Xóa agent (auto detect system) |
| `/pause <slug>` | Tạm dừng agent |
| `/resume <slug>` | Chạy lại agent |
| `/budget <slug> <cents>` | Đặt budget tháng (Paperclip agents) |
| `/status` | Dashboard: PC backbone + OF reviewer + tasks |
| `/models` | Xem models khả dụng (OpenFang catalog) |
| `/kick <slug>` | Gọi agent chạy ngay |
| `/cost` | Chi phí: Paperclip ($$) + OpenFang (tokens) |
| `/approve` | Duyệt → chuyển phase tiếp |
| `/reject` | Reject → thiết kế lại |

## Debate Flow (cross-system)

Khi submit `/idea`, hệ thống tự động:

1. Paperclip tạo Company → Goal → Project → Issue hierarchy
2. Paperclip spawn CTO, Engineer, QA agents (backbone, HTTP adapter → CLIProxyAPI)
3. OpenFang spawn Critic agent (reviewer, TOML manifest → CLIProxyAPI)
4. Tạo 4 Telegram forum topics
5. **CTO (Paperclip, o3)** thiết kế kiến trúc
6. **Critic (OpenFang, gpt-4o)** phản biện thiết kế
7. 2-6 rounds tranh luận xuyên hệ thống, 30s cooldown
8. Khi thống nhất → user `/approve` → **Engineer (Paperclip)** code → **QA (Paperclip)** test

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
│   ├── openfang.py         # OpenFang client (Critic reviewer)
│   ├── paperclip.py        # Paperclip client (backbone + invoke_agent)
│   ├── telegram_bot.py     # Telegram bot + handlers
│   ├── topic_manager.py    # Topic auto-creation
│   ├── debate.py           # Cross-system CTO↔Critic debate
│   ├── commands.py         # /agents /model /hire etc. (dual system)
│   ├── agents.py           # Agents split by system + prompts
│   └── kv.py               # JSON KV store (orchestrator state)
├── scripts/
│   ├── install.ps1         # Windows installer
│   └── start.ps1           # Start all services
└── data/
    └── kv.json             # Runtime state (gitignored)
```

## License

MIT
