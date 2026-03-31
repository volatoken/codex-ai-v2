"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_GROUP_ID: int = int(os.getenv("TELEGRAM_GROUP_ID", "0"))
TELEGRAM_ADMIN_USER_ID: int = int(os.getenv("TELEGRAM_ADMIN_USER_ID", "0"))

# CLIProxyAPI
CLIPROXY_URL: str = os.getenv("CLIPROXY_URL", "http://127.0.0.1:8317")
CLIPROXY_OPENFANG_KEY: str = os.getenv("CLIPROXY_OPENFANG_KEY", "openfang-key-2026")
CLIPROXY_PAPERCLIP_KEY: str = os.getenv("CLIPROXY_PAPERCLIP_KEY", "paperclip-key-2026")

# Paperclip
PAPERCLIP_URL: str = os.getenv("PAPERCLIP_URL", "http://127.0.0.1:3100")

# Default models per agent role
DEFAULT_MODEL_CTO: str = os.getenv("DEFAULT_MODEL_CTO", "o3")
DEFAULT_MODEL_ENGINEER: str = os.getenv("DEFAULT_MODEL_ENGINEER", "gpt-4o")
DEFAULT_MODEL_QA: str = os.getenv("DEFAULT_MODEL_QA", "gpt-4o-mini")
DEFAULT_MODEL_CRITIC: str = os.getenv("DEFAULT_MODEL_CRITIC", "gpt-4o")
DEFAULT_MODEL_GATEWAY: str = os.getenv("DEFAULT_MODEL_GATEWAY", "gpt-4o-mini")

# Debate engine
DEBATE_MAX_ROUNDS: int = int(os.getenv("DEBATE_MAX_ROUNDS", "6"))
DEBATE_COOLDOWN_SEC: int = int(os.getenv("DEBATE_COOLDOWN_SEC", "30"))
DEBATE_SUPERMAJORITY: float = 0.8
