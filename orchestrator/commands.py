"""Telegram command handlers — topic cha = control panel.

Uses OpenFang for agent execution and Paperclip for project management.
"""

import re

from telegram import Update
from telegram.ext import ContextTypes

from . import config, kv
from .agents import build_manifest, SYSTEM_PROMPTS, DEFAULT_AGENTS
from .openfang import OpenFangClient
from .paperclip import PaperclipClient

paperclip = PaperclipClient()
openfang = OpenFangClient()


# ── /agents ──────────────────────────────────────────────────

async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    if not slug:
        return await _reply(update, "\U0001f4ce Không tìm thấy project cho topic này.")

    try:
        of_agents = await openfang.list_agents()
    except Exception as exc:
        return await _reply(update, f"\U0001f4ce Lỗi OpenFang: {exc}")

    if not of_agents:
        return await _reply(update, "\U0001f4ce Chưa có agent nào.")

    lines = ["\U0001f4ce Agents", "\u2501" * 24]
    for a in of_agents:
        icon = {
            "active": "\U0001f7e2", "idle": "\U0001f7e2",
            "running": "\U0001f504", "paused": "\u23f8",
            "error": "\U0001f534",
        }.get(a.get("status", ""), "\u26aa")
        model = a.get("model", {}).get("model", "?") if isinstance(a.get("model"), dict) else a.get("model", "?")
        name = a.get("name", "?")
        lines.append(f"{icon} {name:12s}\u2502 {model:15s}")
    lines.append("\n\u0110\u1ed5i model: /model <agent> <model>")
    lines.append('Tạo mới:   /hire <slug> "<role>" [model]')
    await _reply(update, "\n".join(lines))


# ── /model ───────────────────────────────────────────────────

async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    if not slug:
        return await _reply(update, "\U0001f4ce Không tìm thấy project.")

    args = context.args or []
    if len(args) < 2:
        return await _reply(update, "\U0001f4ce /model <agent> <model>")

    agent_name, new_model = args[0].lower(), args[1]

    of_agent_id = kv.get(f"project:{slug}:of_agents:{agent_name}")
    if not of_agent_id:
        return await _reply(update, f"\U0001f4ce Agent '{agent_name}' không tồn tại.")

    try:
        old_model = kv.get(f"project:{slug}:model:{agent_name}", "?")
        await openfang.switch_model(of_agent_id, new_model)
        kv.set(f"project:{slug}:model:{agent_name}", new_model)
        await _reply(
            update,
            f"\U0001f4ce \u2705 {agent_name} model: {old_model} \u2192 {new_model}",
        )
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── /hire ────────────────────────────────────────────────────

async def cmd_hire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    if not slug:
        return await _reply(update, "\U0001f4ce Không tìm thấy project.")

    text = update.message.text or ""
    match = re.match(r'/hire\s+(\S+)\s+"([^"]+)"(?:\s+(\S+))?', text)
    if not match:
        match = re.match(r"/hire\s+(\S+)\s+(\S+)(?:\s+(\S+))?", text)
    if not match:
        return await _reply(update, '\U0001f4ce /hire <slug> "<role>" [model]')

    agent_slug = match.group(1)
    role = match.group(2)
    model = match.group(3) or config.DEFAULT_MODEL_ENGINEER
    company_id = kv.get(f"project:{slug}:company_id")

    try:
        # 1. Spawn in OpenFang
        prompt = SYSTEM_PROMPTS.get(role.lower(), f"Bạn là {role}.")
        manifest = build_manifest(agent_slug, role, model)
        of_agent = await openfang.spawn_agent(manifest)
        of_id = of_agent["id"]
        await openfang.update_agent(of_id, system_prompt=prompt)

        # 2. Register in Paperclip for budget tracking
        pc_agent = await paperclip.create_agent(
            company_id,
            {
                "name": agent_slug.capitalize(),
                "role": role,
                "adapterType": "http",
                "budgetMonthlyCents": 500,
            },
        )

        # 3. Save mappings
        kv.set(f"project:{slug}:of_agents:{agent_slug}", of_id)
        kv.set(f"project:{slug}:pc_agents:{agent_slug}", pc_agent["id"])
        kv.set(f"project:{slug}:model:{agent_slug}", model)
        await _reply(
            update,
            f"\U0001f4ce \u2705 Hired: {agent_slug.capitalize()} ({model})\n"
            f"   Role: {role}\n"
            f"   Budget: $5.00/tháng\n"
            f"   /fire {agent_slug} để xóa",
        )
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi tạo agent: {exc}")


# ── /fire ────────────────────────────────────────────────────

async def cmd_fire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    args = context.args or []
    if not slug or not args:
        return await _reply(update, "\U0001f4ce /fire <agent>")

    name = args[0].lower()
    of_id = kv.get(f"project:{slug}:of_agents:{name}")
    pc_id = kv.get(f"project:{slug}:pc_agents:{name}")
    if not of_id and not pc_id:
        return await _reply(update, f"\U0001f4ce Agent '{name}' không tồn tại.")

    try:
        if of_id:
            await openfang.kill_agent(of_id)
        if pc_id:
            await paperclip.terminate_agent(pc_id)
        kv.delete(f"project:{slug}:of_agents:{name}")
        kv.delete(f"project:{slug}:pc_agents:{name}")
        kv.delete(f"project:{slug}:model:{name}")
        await _reply(update, f"\U0001f4ce \u2705 Terminated: {name}")
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── /pause & /resume ────────────────────────────────────────

async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    args = context.args or []
    if not slug or not args:
        return await _reply(update, "\U0001f4ce /pause <agent>")

    name = args[0].lower()
    of_id = kv.get(f"project:{slug}:of_agents:{name}")
    if not of_id:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        await openfang.stop_agent(of_id)
        await _reply(update, f"\U0001f4ce \u23f8 Paused: {args[0]}")
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    args = context.args or []
    if not slug or not args:
        return await _reply(update, "\U0001f4ce /resume <agent>")

    name = args[0].lower()
    of_id = kv.get(f"project:{slug}:of_agents:{name}")
    if not of_id:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        await openfang.reset_session(of_id)
        await _reply(update, f"\U0001f4ce \u2705 Resumed: {args[0]}")
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── /budget ──────────────────────────────────────────────────

async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    args = context.args or []
    if not slug or len(args) < 2:
        return await _reply(update, "\U0001f4ce /budget <agent> <cents>")

    pc_id = kv.get(f"project:{slug}:pc_agents:{args[0].lower()}")
    if not pc_id:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        cents = int(args[1])
    except ValueError:
        return await _reply(update, "\U0001f4ce Budget phải là số (cents).")

    try:
        await paperclip.set_agent_budget(pc_id, cents)
        await _reply(
            update,
            f"\U0001f4ce \u2705 Budget {args[0]}: ${cents / 100:.2f}/tháng",
        )
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── /status ──────────────────────────────────────────────────

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    if not slug:
        return await _reply(update, "\U0001f4ce Không tìm thấy project.")

    company_id = kv.get(f"project:{slug}:company_id")
    phase = kv.get(f"project:{slug}:phase", "architecture")
    title = kv.get(f"project:{slug}:title", slug)

    try:
        of_agents = await openfang.list_agents()
        of_status = await openfang.status()
        dash = await paperclip.get_dashboard(company_id) if company_id else {}
        await _reply(
            update,
            f"\U0001f4ce Dashboard — {title}\n"
            + "\u2501" * 28
            + f"\n\U0001f4ca Phase:      {phase}"
            f"\n\U0001f916 OF Agents:  {len(of_agents)} running"
            f"\n\U0001f4cb Tasks:      {dash.get('openIssues', 0)} open "
            f"\u2502 {dash.get('doneIssues', 0)} done"
            f"\n\U0001f4b0 Tháng này:  "
            f"${dash.get('monthSpendCents', 0) / 100:.2f}",
        )
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── /models ──────────────────────────────────────────────────

async def cmd_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        models = await openfang.list_models()
        lines = ["\U0001f4ce Models khả dụng (OpenFang):", "\u2501" * 18]
        for m in models[:30]:
            name = m.get("id", m) if isinstance(m, dict) else m
            lines.append(f"  \u2022 {name}")
        if len(models) > 30:
            lines.append(f"  ... và {len(models) - 30} model khác")
        await _reply(update, "\n".join(lines))
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi OpenFang: {exc}")


# ── /kick ────────────────────────────────────────────────────

async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    args = context.args or []
    if not slug or not args:
        return await _reply(update, "\U0001f4ce /kick <agent>")

    of_id = kv.get(f"project:{slug}:of_agents:{args[0].lower()}")
    if not of_id:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        await openfang.send_message(of_id, "Wake up — user kicked you. Report status.")
        await _reply(
            update,
            f"\U0001f4ce \U0001f504 Kicked: {args[0]} — wake message sent",
        )
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── /cost ────────────────────────────────────────────────────

async def cmd_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    if not slug:
        return await _reply(update, "\U0001f4ce Không tìm thấy project.")

    try:
        usage = await openfang.get_usage("month")
        by_model = await openfang.get_usage_by_model()
        lines = [
            "\U0001f4ce Chi phí tháng này (OpenFang)",
            "\u2501" * 28,
            f"Tokens: {usage.get('total_tokens', 0):,}",
        ]
        for m in by_model[:10]:
            name = m.get("model", "?")
            tokens = m.get("tokens", 0)
            lines.append(f"  \u2022 {name}: {tokens:,} tokens")
        await _reply(update, "\n".join(lines))
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── utilities ────────────────────────────────────────────────

def _get_slug(update: Update) -> str | None:
    tid = update.message.message_thread_id if update.message else None
    if tid:
        return kv.get(f"topic_to_project:{tid}")
    return None


async def _reply(update: Update, text: str) -> None:
    if update.message:
        await update.message.reply_text(text)
