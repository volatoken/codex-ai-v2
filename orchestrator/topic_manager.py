"""Telegram forum-topic lifecycle: create parent + sub-topics per idea."""

from telegram import Bot
from . import config, kv


class TopicManager:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.group_id = config.TELEGRAM_GROUP_ID

    async def create_idea_topics(self, slug: str, title: str) -> dict:
        """Create parent topic + Architecture / Code / Test sub-topics."""
        short = title[:50]

        parent = await self.bot.create_forum_topic(
            chat_id=self.group_id, name=f"\U0001f4cc {short}"
        )
        arch = await self.bot.create_forum_topic(
            chat_id=self.group_id, name=f"\U0001f4d0 {short} — Architecture"
        )
        code = await self.bot.create_forum_topic(
            chat_id=self.group_id, name=f"\U0001f4bb {short} — Code"
        )
        test = await self.bot.create_forum_topic(
            chat_id=self.group_id, name=f"\U0001f9ea {short} — Test & Deploy"
        )

        topic_ids = {
            "parent": parent.message_thread_id,
            "architecture": arch.message_thread_id,
            "code": code.message_thread_id,
            "test": test.message_thread_id,
        }

        # Persist bi-directional mappings
        kv.set(f"project:{slug}:topics", topic_ids)
        for tid in topic_ids.values():
            kv.set(f"topic_to_project:{tid}", slug)

        # Welcome message in parent topic
        await self.bot.send_message(
            chat_id=self.group_id,
            message_thread_id=parent.message_thread_id,
            text=(
                f"\U0001f4ce Project: {title}\n"
                "\u2501" * 24 + "\n"
                "\U0001f4d0 Architecture \u2192 topic ri\u00eang\n"
                "\U0001f4bb Code \u2192 topic ri\u00eang\n"
                "\U0001f9ea Test & Deploy \u2192 topic ri\u00eang\n\n"
                "L\u1ec7nh qu\u1ea3n l\u00fd:\n"
                "/agents \u2014 xem agents\n"
                "/model <agent> <model> \u2014 \u0111\u1ed5i model\n"
                "/hire <slug> <role> [model] \u2014 th\u00eam agent\n"
                "/status \u2014 dashboard\n"
                "/approve \u2014 duy\u1ec7t thi\u1ebft k\u1ebf\n"
            ),
        )

        return topic_ids

    def get_project_slug(self, topic_id: int) -> str | None:
        return kv.get(f"topic_to_project:{topic_id}")

    def get_topic_type(self, topic_id: int, slug: str) -> str:
        topics = kv.get(f"project:{slug}:topics", {})
        for ttype, tid in topics.items():
            if tid == topic_id:
                return ttype
        return "unknown"
