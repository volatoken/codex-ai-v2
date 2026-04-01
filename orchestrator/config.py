"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_GROUP_ID: int = int(os.getenv("TELEGRAM_GROUP_ID", "0"))
TELEGRAM_ADMIN_USER_ID: int = int(os.getenv("TELEGRAM_ADMIN_USER_ID", "0"))

# OpenFang — Agent execution engine
OPENFANG_URL: str = os.getenv("OPENFANG_URL", "http://127.0.0.1:4200")
OPENFANG_API_KEY: str = os.getenv("OPENFANG_API_KEY", "")

# CLIProxyAPI — ChatGPT proxy (configured as OpenFang provider)
CLIPROXY_URL: str = os.getenv("CLIPROXY_URL", "http://127.0.0.1:8317")
CLIPROXY_API_KEY: str = os.getenv("CLIPROXY_API_KEY", "openfang-key-2026")

# Paperclip — Project management control plane
PAPERCLIP_URL: str = os.getenv("PAPERCLIP_URL", "http://127.0.0.1:3100")

# Default models per agent role (used by OpenFang agents)
DEFAULT_MODEL_CTO: str = os.getenv("DEFAULT_MODEL_CTO", "o3")
DEFAULT_MODEL_ENGINEER: str = os.getenv("DEFAULT_MODEL_ENGINEER", "gpt-4o")
DEFAULT_MODEL_QA: str = os.getenv("DEFAULT_MODEL_QA", "gpt-4o-mini")
DEFAULT_MODEL_CRITIC: str = os.getenv("DEFAULT_MODEL_CRITIC", "gpt-4o")
DEFAULT_MODEL_SECURITY: str = os.getenv("DEFAULT_MODEL_SECURITY", "gpt-4o")
DEFAULT_MODEL_PERFORMANCE: str = os.getenv("DEFAULT_MODEL_PERFORMANCE", "gpt-4o-mini")

# Debate engine
DEBATE_MAX_ROUNDS: int = int(os.getenv("DEBATE_MAX_ROUNDS", "6"))
DEBATE_COOLDOWN_SEC: int = int(os.getenv("DEBATE_COOLDOWN_SEC", "30"))
DEBATE_SUPERMAJORITY: float = 0.8
