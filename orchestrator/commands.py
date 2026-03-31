"""Telegram command handlers — topic cha = control panel."""

import re

from telegram import Update
from telegram.ext import ContextTypes

from . import config, kv, llm
from .agents import make_agent_config, DEFAULT_AGENTS
from .paperclip import PaperclipClient

paperclip = PaperclipClient()


# ── /agents ──────────────────────────────────────────────────

async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    if not slug:
        return await _reply(update, "\U0001f4ce Không tìm thấy project cho topic này.")

    company_id = kv.get(f"project:{slug}:company_id")
    if not company_id:
        return await _reply(update, "\U0001f4ce Chưa setup company.")

    try:
        agents = await paperclip.get_agents(company_id)
    except Exception as exc:
        return await _reply(update, f"\U0001f4ce Lỗi Paperclip: {exc}")

    if not agents:
        return await _reply(update, "\U0001f4ce Chưa có agent nào.")

    lines = ["\U0001f4ce Agents", "\u2501" * 24]
    for a in agents:
        icon = {
            "active": "\U0001f7e2", "idle": "\U0001f7e2",
            "running": "\U0001f504", "paused": "\u23f8",
            "error": "\U0001f534",
        }.get(a.get("status", ""), "\u26aa")
        model = _extract_model(a)
        spent = a.get("spentMonthlyCents", 0)
        budget = a.get("budgetMonthlyCents", 0)
        lines.append(
            f"{icon} {a['name']:12s}\u2502 {model:15s}\u2502 "
            f"${spent / 100:.2f}/${budget / 100:.2f}"
        )
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
    company_id = kv.get(f"project:{slug}:company_id")

    try:
        agents = await paperclip.get_agents(company_id)
        agent = next((a for a in agents if a["name"].lower() == agent_name), None)
        if not agent:
            return await _reply(update, f"\U0001f4ce Agent '{agent_name}' không tồn tại.")

        ac = agent.get("adapterConfig", agent.get("adapter_config", {}))
        pt = ac.get("payloadTemplate", {})
        old_model = pt.get("model", "?")
        pt["model"] = new_model
        ac["payloadTemplate"] = pt
        await paperclip.update_agent(agent["id"], {"adapterConfig": ac})
        kv.set(f"project:{slug}:model:{agent_name}", new_model)
        await _reply(
            update,
            f"\U0001f4ce \u2705 {agent['name']} model: {old_model} \u2192 {new_model}",
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
    cto_id = kv.get(f"project:{slug}:agents:cto")

    try:
        agent = await paperclip.create_agent(
            company_id,
            {
                "name": agent_slug.capitalize(),
                "role": role,
                "adapterType": "http",
                "adapterConfig": make_agent_config(role, model),
                "reportsTo": cto_id,
                "budgetMonthlyCents": 500,
            },
        )
        kv.set(f"project:{slug}:agents:{agent_slug}", agent["id"])
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
    agent_id = kv.get(f"project:{slug}:agents:{name}")
    if not agent_id:
        return await _reply(update, f"\U0001f4ce Agent '{name}' không tồn tại.")

    try:
        await paperclip.terminate_agent(agent_id)
        kv.delete(f"project:{slug}:agents:{name}")
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

    agent_id = kv.get(f"project:{slug}:agents:{args[0].lower()}")
    if not agent_id:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        await paperclip.pause_agent(agent_id)
        await _reply(update, f"\U0001f4ce \u23f8 Paused: {args[0]}")
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    args = context.args or []
    if not slug or not args:
        return await _reply(update, "\U0001f4ce /resume <agent>")

    agent_id = kv.get(f"project:{slug}:agents:{args[0].lower()}")
    if not agent_id:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        await paperclip.resume_agent(agent_id)
        await _reply(update, f"\U0001f4ce \u2705 Resumed: {args[0]}")
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── /budget ──────────────────────────────────────────────────

async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    args = context.args or []
    if not slug or len(args) < 2:
        return await _reply(update, "\U0001f4ce /budget <agent> <cents>")

    agent_id = kv.get(f"project:{slug}:agents:{args[0].lower()}")
    if not agent_id:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        cents = int(args[1])
    except ValueError:
        return await _reply(update, "\U0001f4ce Budget phải là số (cents).")

    try:
        await paperclip.set_agent_budget(agent_id, cents)
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
        dash = await paperclip.get_dashboard(company_id)
        await _reply(
            update,
            f"\U0001f4ce Dashboard — {title}\n"
            + "\u2501" * 28
            + f"\n\U0001f4ca Phase:      {phase}"
            f"\n\U0001f916 Agents:     {dash.get('activeAgents', 0)} active"
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
        models = await llm.list_models()
        lines = ["\U0001f4ce Models khả dụng:", "\u2501" * 18]
        for m in models[:20]:
            lines.append(f"  \u2022 {m}")
        if len(models) > 20:
            lines.append(f"  ... và {len(models) - 20} model khác")
        await _reply(update, "\n".join(lines))
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi CLIProxyAPI: {exc}")


# ── /kick ────────────────────────────────────────────────────

async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    args = context.args or []
    if not slug or not args:
        return await _reply(update, "\U0001f4ce /kick <agent>")

    agent_id = kv.get(f"project:{slug}:agents:{args[0].lower()}")
    if not agent_id:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        await paperclip.invoke_heartbeat(agent_id)
        await _reply(
            update,
            f"\U0001f4ce \U0001f504 Kicked: {args[0]} — heartbeat invoked",
        )
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── /cost ────────────────────────────────────────────────────

async def cmd_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    if not slug:
        return await _reply(update, "\U0001f4ce Không tìm thấy project.")

    company_id = kv.get(f"project:{slug}:company_id")
    try:
        costs = await paperclip.get_cost_summary(company_id)
        await _reply(
            update,
            f"\U0001f4ce Chi phí tháng này\n"
            + "\u2501" * 18
            + f"\nTổng: ${costs.get('totalCents', 0) / 100:.2f}",
        )
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── utilities ────────────────────────────────────────────────

def _get_slug(update: Update) -> str | None:
    tid = update.message.message_thread_id if update.message else None
    if tid:
        return kv.get(f"topic_to_project:{tid}")
    return None


def _extract_model(agent: dict) -> str:
    ac = agent.get("adapterConfig", agent.get("adapter_config", {}))
    return ac.get("payloadTemplate", {}).get("model", "?")


async def _reply(update: Update, text: str) -> None:
    if update.message:
        await update.message.reply_text(text)
