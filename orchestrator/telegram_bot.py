"""Telegram bot — forum-topic-aware, wires commands + debate."""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from . import commands, config, kv
from .agents import DEFAULT_AGENTS, PAPERCLIP_AGENTS, OPENFANG_AGENTS
from .agents import build_manifest, SYSTEM_PROMPTS
from .debate import Debate, DebateManager, DebateState
from .openfang import OpenFangClient
from .paperclip import PaperclipClient, make_agent_config
from .topic_manager import TopicManager

logger = logging.getLogger(__name__)
paperclip = PaperclipClient()
openfang = OpenFangClient()


class TelegramBot:
    def __init__(self) -> None:
        self.app = (
            Application.builder()
            .token(config.TELEGRAM_BOT_TOKEN)
            .build()
        )
        self.topic_mgr: TopicManager | None = None
        self.debate_mgr: DebateManager | None = None
        self._register_handlers()

    # ── handler registration ─────────────────────────────────

    def _register_handlers(self) -> None:
        add = self.app.add_handler
        add(CommandHandler("idea", self._on_idea))
        add(CommandHandler("approve", self._on_approve))
        add(CommandHandler("reject", self._on_reject))
        add(CommandHandler("agents", commands.cmd_agents))
        add(CommandHandler("model", commands.cmd_model))
        add(CommandHandler("hire", commands.cmd_hire))
        add(CommandHandler("fire", commands.cmd_fire))
        add(CommandHandler("pause", commands.cmd_pause))
        add(CommandHandler("resume", commands.cmd_resume))
        add(CommandHandler("budget", commands.cmd_budget))
        add(CommandHandler("status", commands.cmd_status))
        add(CommandHandler("models", commands.cmd_models))
        add(CommandHandler("kick", commands.cmd_kick))
        add(CommandHandler("cost", commands.cmd_cost))

        # Non-command text in the supergroup (user replies in debate)
        add(
            MessageHandler(
                filters.TEXT
                & ~filters.COMMAND
                & filters.Chat(chat_id=config.TELEGRAM_GROUP_ID),
                self._on_message,
            )
        )

    # ── lifecycle ────────────────────────────────────────────

    async def _post_init(self, app: Application) -> None:
        self.topic_mgr = TopicManager(app.bot)
        self.debate_mgr = DebateManager(self._send, paperclip, openfang)

        # Configure CLIProxyAPI as OpenFang's OpenAI provider
        if config.CLIPROXY_API_KEY:
            try:
                await openfang.set_provider_key("openai", config.CLIPROXY_API_KEY)
            except Exception:
                logger.warning("Could not set OpenFang provider key")

    async def _send(self, topic_id: int, text: str) -> None:
        for chunk in _chunk(text, 4000):
            await self.app.bot.send_message(
                chat_id=config.TELEGRAM_GROUP_ID,
                message_thread_id=topic_id,
                text=chunk,
            )

    # ── /idea ────────────────────────────────────────────────

    async def _on_idea(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.message or not update.message.text:
            return
        if update.message.from_user.id != config.TELEGRAM_ADMIN_USER_ID:
            return await update.message.reply_text(
                "\U0001f4ce Chỉ admin mới được submit idea."
            )

        text = update.message.text.replace("/idea", "", 1).strip()
        if not text:
            return await update.message.reply_text(
                "\U0001f4ce /idea <mô tả ý tưởng>"
            )

        import re

        slug = re.sub(r"[^a-z0-9]+", "-", text[:50].lower()).strip("-")
        await update.message.reply_text(
            f"\U0001f4ce Đang tạo project '{slug}'..."
        )

        try:
            # 1. Paperclip — company + goal + project
            company = await paperclip.create_company(
                name=text[:100], description=text
            )
            cid = company["id"]

            goal = await paperclip.create_goal(
                cid,
                {"title": text[:200], "level": "company", "status": "active"},
            )
            project = await paperclip.create_project(
                cid,
                {
                    "name": text[:100],
                    "description": text,
                    "goalId": goal["id"],
                    "status": "planned",
                },
            )

            # 2. Spawn agents — Paperclip backbone vs OpenFang reviewer
            for a_slug, a_def in DEFAULT_AGENTS.items():
                if a_def["system"] == "paperclip":
                    # Paperclip = backbone (CTO, Engineer, QA)
                    # HTTP adapter → CLIProxyAPI → ChatGPT
                    pc_agent = await paperclip.create_agent(
                        cid,
                        {
                            "name": a_def["display_name"],
                            "role": a_slug,
                            "adapterType": "http",
                            "adapterConfig": make_agent_config(
                                a_def["system_prompt"], a_def["model"]
                            ),
                            "budgetMonthlyCents": a_def["budget_monthly_cents"],
                        },
                    )
                    kv.set(f"project:{slug}:pc_agents:{a_slug}", pc_agent["id"])
                    kv.set(f"project:{slug}:model:{a_slug}", a_def["model"])

                else:
                    # OpenFang = reviewer (Critic)
                    manifest = build_manifest(
                        a_def["name"], a_def["description"], a_def["model"]
                    )
                    of_agent = await openfang.spawn_agent(manifest)
                    of_id = of_agent["id"]
                    await openfang.update_agent(
                        of_id, system_prompt=a_def["system_prompt"]
                    )
                    kv.set(f"project:{slug}:of_agents:{a_slug}", of_id)
                    kv.set(f"project:{slug}:model:{a_slug}", a_def["model"])

            # 3. Persist project metadata
            kv.set(f"project:{slug}:company_id", cid)
            kv.set(f"project:{slug}:project_id", project["id"])
            kv.set(f"project:{slug}:goal_id", goal["id"])
            kv.set(f"project:{slug}:title", text[:100])
            kv.set(f"project:{slug}:phase", "architecture")

            # 4. Telegram topics
            topic_ids = await self.topic_mgr.create_idea_topics(
                slug, text[:50]
            )

            # 5. Architecture issue
            issue = await paperclip.create_issue(
                cid,
                {
                    "title": f"Architecture: {text[:100]}",
                    "description": text,
                    "projectId": project["id"],
                    "goalId": goal["id"],
                    "status": "todo",
                    "priority": "high",
                },
            )
            kv.set(f"project:{slug}:arch_issue_id", issue["id"])

            # 6. Kick off CTO ↔ Critic debate
            await self.debate_mgr.start_debate(
                slug, text, topic_ids["architecture"]
            )

        except Exception:
            logger.exception("Error in /idea")
            await update.message.reply_text(
                "\U0001f4ce Lỗi tạo project. Xem log để biết chi tiết."
            )

    # ── /approve & /reject ───────────────────────────────────

    async def _on_approve(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        slug = _slug(update)
        if not slug:
            return await update.message.reply_text(
                "\U0001f4ce Không tìm thấy project."
            )

        phase = kv.get(f"project:{slug}:phase", "architecture")
        topics = kv.get(f"project:{slug}:topics", {})

        if phase == "architecture":
            kv.set(f"project:{slug}:phase", "code")
            if topics.get("code"):
                await self._send(
                    topics["code"],
                    "\U0001f4ce \u2705 Kiến trúc approved!\n"
                    "   Phase: Code — Engineer bắt đầu implement.",
                )
            await update.message.reply_text(
                "\U0001f4ce \u2705 Approved! → phase Code"
            )

        elif phase == "code":
            kv.set(f"project:{slug}:phase", "test")
            if topics.get("test"):
                await self._send(
                    topics["test"],
                    "\U0001f4ce \u2705 Code approved!\n"
                    "   Phase: Test & Deploy — QA bắt đầu test.",
                )
            await update.message.reply_text(
                "\U0001f4ce \u2705 Approved! → phase Test"
            )

    async def _on_reject(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        slug = _slug(update)
        if not slug:
            return await update.message.reply_text(
                "\U0001f4ce Không tìm thấy project."
            )

        topics = kv.get(f"project:{slug}:topics", {})
        if topics.get("architecture"):
            await self._send(
                topics["architecture"],
                "\U0001f4ce \u274c Thiết kế bị reject. CTO hãy thiết kế lại.",
            )
        await update.message.reply_text(
            "\U0001f4ce \u274c Rejected. CTO sẽ thiết kế lại."
        )

    # ── free-text handler (debate user replies) ──────────────

    async def _on_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.message or not update.message.text:
            return
        if update.message.text.startswith("\U0001f4ce"):
            return  # ignore own bot messages

        slug = _slug(update)
        if not slug:
            return

        tid = update.message.message_thread_id
        topics = kv.get(f"project:{slug}:topics", {})

        if tid == topics.get("architecture"):
            debate = Debate.load(slug)
            if debate and debate.state == DebateState.WAITING_USER:
                await self.debate_mgr.user_reply(
                    slug, update.message.text, tid
                )

    # ── run ───────────────────────────────────────────────────

    def run(self) -> None:
        self.app.post_init = self._post_init
        self.app.run_polling(drop_pending_updates=True)


# ── module helpers ───────────────────────────────────────────

def _slug(update: Update) -> str | None:
    tid = update.message.message_thread_id if update.message else None
    if tid:
        return kv.get(f"topic_to_project:{tid}")
    return None


def _chunk(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts
