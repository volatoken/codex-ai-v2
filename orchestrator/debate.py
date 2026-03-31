"""CTO ↔ Critic debate state machine.

Rules
─────
1. Max 6 rounds (configurable).
2. Each round must reduce open issues; re-raised issues auto-resolve.
3. Supermajority (>=80 % resolved) → auto-agree.
4. After 4 rounds with >2 open issues → escalate to user.
5. 30 s cooldown between rounds.

Execution: CTO and Critic are OpenFang agents.
Orchestrator sends messages via OpenFang API → agents call LLM → return text.
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable

from . import config, kv
from .openfang import OpenFangClient


class DebateState(str, Enum):
    IDLE = "idle"
    CTO_TURN = "cto_turn"
    CRITIC_TURN = "critic_turn"
    WAITING_USER = "waiting_user"
    AGREED = "agreed"
    FORCE_CONCLUDE = "force_conclude"


@dataclass
class Issue:
    id: int
    title: str
    raised_by: str  # "critic" | "cto"
    status: str = "open"  # open | resolved | deferred
    cto_response: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "raised_by": self.raised_by,
            "status": self.status,
            "cto_response": self.cto_response,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Issue":
        return cls(
            id=d["id"],
            title=d["title"],
            raised_by=d["raised_by"],
            status=d.get("status", "open"),
            cto_response=d.get("cto_response", ""),
        )


@dataclass
class Debate:
    slug: str
    state: DebateState = DebateState.IDLE
    round: int = 0
    issues: list[Issue] = field(default_factory=list)
    design_history: list[str] = field(default_factory=list)
    user_answers: list[str] = field(default_factory=list)
    started_at: float = 0.0
    last_activity: float = 0.0

    # ── persistence ──────────────────────────────────────────

    def save(self) -> None:
        kv.set(
            f"debate:{self.slug}",
            {
                "state": self.state.value,
                "round": self.round,
                "issues": [i.to_dict() for i in self.issues],
                "design_history": self.design_history,
                "user_answers": self.user_answers,
                "started_at": self.started_at,
                "last_activity": self.last_activity,
            },
        )

    @classmethod
    def load(cls, slug: str) -> "Debate | None":
        raw = kv.get(f"debate:{slug}")
        if raw is None:
            return None
        d = cls(slug=slug)
        d.state = DebateState(raw["state"])
        d.round = raw["round"]
        d.issues = [Issue.from_dict(i) for i in raw.get("issues", [])]
        d.design_history = raw.get("design_history", [])
        d.user_answers = raw.get("user_answers", [])
        d.started_at = raw.get("started_at", 0.0)
        d.last_activity = raw.get("last_activity", 0.0)
        return d

    # ── helpers ──────────────────────────────────────────────

    @property
    def open_issues(self) -> list[Issue]:
        return [i for i in self.issues if i.status == "open"]

    @property
    def resolved_issues(self) -> list[Issue]:
        return [i for i in self.issues if i.status == "resolved"]

    @property
    def convergence(self) -> float:
        if not self.issues:
            return 1.0
        return len(self.resolved_issues) / len(self.issues)


# Circled-number prefixes used by critic / CTO
_CIRCLES = "①②③④⑤⑥⑦⑧⑨⑩"
_ISSUE_RE = re.compile(
    r"[①②③④⑤⑥⑦⑧⑨⑩]\s*\[(OPEN|RESOLVED)\]\s*(.+?)(?:\n|$)"
)


SendFn = Callable[[int, str], Awaitable[None]]


class DebateManager:
    """Orchestrates the CTO ↔ Critic debate loop via OpenFang agents."""

    def __init__(self, send_message: SendFn, openfang: OpenFangClient) -> None:
        self.send_message = send_message
        self.of = openfang

    # ── public entry points ──────────────────────────────────

    async def start_debate(
        self, slug: str, idea: str, topic_id: int
    ) -> Debate:
        debate = Debate(slug=slug)
        debate.started_at = time.time()
        debate.last_activity = time.time()
        debate.state = DebateState.CTO_TURN
        debate.round = 1
        debate.save()

        # Round 1 — CTO produces initial design
        cto_text = await self._call_cto(idea, debate)
        debate.design_history.append(cto_text)
        debate.last_activity = time.time()
        debate.save()
        await self.send_message(topic_id, cto_text)

        await asyncio.sleep(config.DEBATE_COOLDOWN_SEC)

        # Round 2 — Critic reviews
        debate.state = DebateState.CRITIC_TURN
        debate.round = 2
        debate.save()

        critic_text = await self._call_critic(cto_text, debate)
        self._parse_issues(debate, critic_text)
        debate.last_activity = time.time()
        debate.save()
        await self.send_message(topic_id, critic_text)

        # Check whether Critic needs user input
        user_qs = _extract_user_questions(critic_text)
        if user_qs:
            debate.state = DebateState.WAITING_USER
            debate.save()
            await self.send_message(
                topic_id,
                "\U0001f4ce @User — Critic cần bạn làm rõ:\n"
                + "\n".join(f"   {i + 1}. {q}" for i, q in enumerate(user_qs)),
            )
            return debate

        if debate.convergence >= config.DEBATE_SUPERMAJORITY:
            debate.state = DebateState.AGREED
            debate.save()
            await self._announce_agreement(debate, topic_id)
            return debate

        # Continue the back-and-forth
        await self._continue(debate, topic_id)
        return debate

    async def user_reply(
        self, slug: str, answer: str, topic_id: int
    ) -> None:
        debate = Debate.load(slug)
        if debate is None or debate.state != DebateState.WAITING_USER:
            return
        debate.user_answers.append(answer)
        debate.last_activity = time.time()
        debate.state = DebateState.CTO_TURN
        debate.round += 1
        debate.save()

        await asyncio.sleep(config.DEBATE_COOLDOWN_SEC)
        await self._continue(debate, topic_id)

    # ── internal loop ────────────────────────────────────────

    async def _continue(self, debate: Debate, topic_id: int) -> None:
        terminal = {
            DebateState.AGREED,
            DebateState.FORCE_CONCLUDE,
            DebateState.WAITING_USER,
        }
        while debate.state not in terminal:
            if debate.round > config.DEBATE_MAX_ROUNDS:
                debate.state = DebateState.FORCE_CONCLUDE
                debate.save()
                await self._force_conclude(debate, topic_id)
                return

            if debate.state == DebateState.CTO_TURN:
                ctx = self._build_cto_context(debate)
                cto_text = await self._call_cto(ctx, debate)
                debate.design_history.append(cto_text)
                debate.last_activity = time.time()
                debate.round += 1
                debate.state = DebateState.CRITIC_TURN
                debate.save()
                await self.send_message(topic_id, cto_text)
                await asyncio.sleep(config.DEBATE_COOLDOWN_SEC)

            elif debate.state == DebateState.CRITIC_TURN:
                latest = debate.design_history[-1] if debate.design_history else ""
                critic_text = await self._call_critic(latest, debate)
                self._parse_issues(debate, critic_text)
                debate.last_activity = time.time()
                debate.round += 1
                debate.save()
                await self.send_message(topic_id, critic_text)

                # User questions?
                user_qs = _extract_user_questions(critic_text)
                if user_qs:
                    debate.state = DebateState.WAITING_USER
                    debate.save()
                    await self.send_message(
                        topic_id,
                        "\U0001f4ce @User — Critic cần bạn làm rõ:\n"
                        + "\n".join(
                            f"   {i + 1}. {q}" for i, q in enumerate(user_qs)
                        ),
                    )
                    return

                # Supermajority?
                if debate.convergence >= config.DEBATE_SUPERMAJORITY:
                    debate.state = DebateState.AGREED
                    debate.save()
                    await self._announce_agreement(debate, topic_id)
                    return

                # Escalate after round 4 with >2 open
                if debate.round >= 4 and len(debate.open_issues) > 2:
                    debate.state = DebateState.WAITING_USER
                    debate.save()
                    lines = "\n".join(
                        f"  \u2022 {i.title}" for i in debate.open_issues
                    )
                    await self.send_message(
                        topic_id,
                        f"\U0001f4ce @User — Sau {debate.round} rounds vẫn "
                        f"còn {len(debate.open_issues)} issues chưa thống "
                        f"nhất:\n{lines}\n\n"
                        "Bạn hãy cho ý kiến để CTO và Critic tiếp tục.",
                    )
                    return

                debate.state = DebateState.CTO_TURN
                debate.save()
                await asyncio.sleep(config.DEBATE_COOLDOWN_SEC)

    # ── LLM calls via OpenFang agents ────────────────────────

    async def _call_cto(self, context: str, debate: Debate) -> str:
        cto_id = kv.get(f"project:{debate.slug}:of_agents:cto")
        if not cto_id:
            raise RuntimeError(f"OpenFang CTO agent not found for {debate.slug}")
        message = (
            f"[Round {debate.round}, Design v"
            f"{len(debate.design_history) + 1}]\n\n{context}"
        )
        return await self.of.send_message(cto_id, message)

    async def _call_critic(self, design: str, debate: Debate) -> str:
        critic_id = kv.get(f"project:{debate.slug}:of_agents:critic")
        if not critic_id:
            raise RuntimeError(f"OpenFang Critic agent not found for {debate.slug}")
        message = (
            f"[Round {debate.round}]\n\n"
            f"Thiết kế CTO:\n\n{design}"
        )
        return await self.of.send_message(critic_id, message)

    # ── context builders ─────────────────────────────────────

    @staticmethod
    def _build_cto_context(debate: Debate) -> str:
        parts: list[str] = []
        if debate.design_history:
            parts.append(f"Thiết kế trước:\n{debate.design_history[-1]}")
        if debate.issues:
            issue_lines = "\n".join(
                f"{_CIRCLES[i.id - 1] if i.id <= 10 else '⓪'} "
                f"{i.title} ({i.status})"
                for i in debate.issues
            )
            parts.append(f"Issues từ Critic:\n{issue_lines}")
        if debate.user_answers:
            parts.append(f"User trả lời:\n{debate.user_answers[-1]}")
        return "\n\n---\n\n".join(parts)

    # ── issue parsing ────────────────────────────────────────

    @staticmethod
    def _parse_issues(debate: Debate, critic_text: str) -> None:
        for status_raw, raw_title in _ISSUE_RE.findall(critic_text):
            title = raw_title.strip().rstrip("\u2705").strip()
            existing = next(
                (i for i in debate.issues if i.title == title), None
            )
            if existing:
                if status_raw == "RESOLVED":
                    existing.status = "resolved"
            else:
                debate.issues.append(
                    Issue(
                        id=len(debate.issues) + 1,
                        title=title,
                        raised_by="critic",
                        status="open" if status_raw == "OPEN" else "resolved",
                    )
                )

        # Global LGTM → resolve everything
        if "LGTM" in critic_text and "\u2705" in critic_text:
            for issue in debate.issues:
                if issue.status == "open":
                    issue.status = "resolved"

    # ── announcements ────────────────────────────────────────

    async def _announce_agreement(
        self, debate: Debate, topic_id: int
    ) -> None:
        r = len(debate.resolved_issues)
        t = len(debate.issues)
        await self.send_message(
            topic_id,
            f"\U0001f4ce \u2705 CTO và Critic đã thống nhất kiến trúc\n"
            f"   {r}/{t} issues resolved trong {debate.round} rounds\n\n"
            f"   @User — xem thiết kế trên và:\n"
            f"   /approve  \u2192 chuyển sang phase Code\n"
            f"   /reject   \u2192 yêu cầu thiết kế lại",
        )

    async def _force_conclude(
        self, debate: Debate, topic_id: int
    ) -> None:
        for i in debate.open_issues:
            i.status = "deferred"
        debate.save()
        await self.send_message(
            topic_id,
            f"\U0001f4ce \u26a0\ufe0f Đã đạt giới hạn "
            f"{config.DEBATE_MAX_ROUNDS} rounds\n"
            f"   {len(debate.open_issues)} issues → deferred\n\n"
            f"   @User — xem thiết kế và quyết định:\n"
            f"   /approve  \u2192 chấp nhận\n"
            f"   /reject   \u2192 thiết kế lại",
        )


# ── helpers (module-level) ───────────────────────────────────

def _extract_user_questions(text: str) -> list[str]:
    questions: list[str] = []
    in_section = False
    for line in text.split("\n"):
        if "CẦN USER LÀM RÕ" in line:
            in_section = True
            continue
        if in_section:
            stripped = line.strip()
            if stripped.startswith(("- ", "\u2022 ")):
                questions.append(stripped.lstrip("-\u2022 ").strip())
            elif stripped.startswith(("Tổng:", "\u2501")) or not stripped:
                break
    return questions
