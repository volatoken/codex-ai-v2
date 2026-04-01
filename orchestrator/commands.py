"""Telegram command handlers — topic cha = control panel.

Uses Paperclip as backbone (CTO, Engineer, QA) and OpenFang for Critic.
"""

import re

from telegram import Update
from telegram.ext import ContextTypes

from . import config, kv
from .agents import build_manifest, SYSTEM_PROMPTS, DEFAULT_AGENTS, OPENFANG_REVIEWER_ROLES
from .openfang import OpenFangClient
from .paperclip import PaperclipClient, make_agent_config

paperclip = PaperclipClient()
openfang = OpenFangClient()


def _agent_system(slug: str, name: str) -> str:
    """Return 'paperclip' or 'openfang' based on where the agent lives."""
    if kv.get(f"project:{slug}:pc_agents:{name}"):
        return "paperclip"
    if kv.get(f"project:{slug}:of_agents:{name}"):
        return "openfang"
    return ""


# ── /agents ──────────────────────────────────────────────────

async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    if not slug:
        return await _reply(update, "\U0001f4ce Không tìm thấy project cho topic này.")

    company_id = kv.get(f"project:{slug}:company_id")
    lines = ["\U0001f4ce Agents", "\u2501" * 34]

    pc_ok, of_ok = True, True

    # Paperclip agents (backbone: CTO, Engineer, QA)
    try:
        pc_agents = await paperclip.get_agents(company_id) if company_id else []
        if pc_agents:
            lines.append("\U0001f3d7 Paperclip (backbone):")
        for a in pc_agents:
            icon = {"active": "\U0001f7e2", "paused": "\u23f8"}.get(
                a.get("status", ""), "\u26aa"
            )
            name = a.get("name", "?")
            role = a.get("role", "?")
            model = kv.get(
                f"project:{slug}:model:{role.lower()}", "?"
            )
            spent = a.get("spentMonthlyCents", 0)
            budget = a.get("budgetMonthlyCents", 0)
            lines.append(
                f"  {icon} {name:10s} {model:14s} "
                f"${spent / 100:.2f}/${budget / 100:.2f}"
            )
    except Exception:
        pc_ok = False
        lines.append("  \u26a0 Paperclip unavailable")

    # OpenFang agents (reviewer: Critic, Security, Performance)
    try:
        of_agents = await openfang.list_agents()
        if of_agents:
            lines.append("\U0001f50d OpenFang (reviewer):")
        for a in of_agents:
            icon = {"active": "\U0001f7e2", "running": "\U0001f504"}.get(
                a.get("status", ""), "\u26aa"
            )
            model = (
                a["model"]["model"]
                if isinstance(a.get("model"), dict)
                else a.get("model", "?")
            )
            name = a.get("name", "?")
            lines.append(f"  {icon} {name:10s} {model:14s}")
    except Exception:
        of_ok = False
        lines.append("  \u26a0 OpenFang unavailable")

    if not pc_ok and not of_ok:
        return await _reply(update, "\U0001f4ce Cả 2 hệ thống đều unavailable.")

    lines.append("")
    lines.append("\U0001f3d7 = backbone (code)  \U0001f50d = reviewer (audit)")
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
    system = _agent_system(slug, agent_name)

    if not system:
        return await _reply(update, f"\U0001f4ce Agent '{agent_name}' không tồn tại.")

    try:
        old_model = kv.get(f"project:{slug}:model:{agent_name}", "?")
        if system == "openfang":
            of_id = kv.get(f"project:{slug}:of_agents:{agent_name}")
            await openfang.switch_model(of_id, new_model)
        else:
            # Paperclip: update adapter config with new model
            pc_id = kv.get(f"project:{slug}:pc_agents:{agent_name}")
            prompt = SYSTEM_PROMPTS.get(agent_name, "")
            await paperclip.update_agent(
                pc_id, {"adapterConfig": make_agent_config(prompt, new_model)}
            )
        kv.set(f"project:{slug}:model:{agent_name}", new_model)
        sys_label = "OF" if system == "openfang" else "PC"
        await _reply(
            update,
            f"\U0001f4ce \u2705 {agent_name} [{sys_label}] model: {old_model} \u2192 {new_model}",
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
    prompt = SYSTEM_PROMPTS.get(role.lower(), f"Bạn là {role}.")

    # Determine system: reviewer/guard roles → OpenFang, rest → Paperclip backbone
    is_reviewer = role.lower() in OPENFANG_REVIEWER_ROLES

    try:
        if is_reviewer:
            # OpenFang reviewer
            manifest = build_manifest(agent_slug, role, model)
            of_agent = await openfang.spawn_agent(manifest)
            of_id = of_agent["id"]
            await openfang.update_agent(of_id, system_prompt=prompt)
            kv.set(f"project:{slug}:of_agents:{agent_slug}", of_id)
            sys_label = "OF"
        else:
            # Paperclip backbone
            pc_agent = await paperclip.create_agent(
                company_id,
                {
                    "name": agent_slug.capitalize(),
                    "role": role,
                    "adapterType": "http",
                    "adapterConfig": make_agent_config(prompt, model),
                    "budgetMonthlyCents": 500,
                },
            )
            kv.set(f"project:{slug}:pc_agents:{agent_slug}", pc_agent["id"])
            sys_label = "PC"

        kv.set(f"project:{slug}:model:{agent_slug}", model)
        await _reply(
            update,
            f"\U0001f4ce \u2705 Hired: {agent_slug.capitalize()} ({model})\n"
            f"   Role: {role}  System: {sys_label}\n"
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
    system = _agent_system(slug, name)
    if not system:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        if system == "openfang":
            await openfang.stop_agent(kv.get(f"project:{slug}:of_agents:{name}"))
        else:
            await paperclip.pause_agent(kv.get(f"project:{slug}:pc_agents:{name}"))
        await _reply(update, f"\U0001f4ce \u23f8 Paused: {args[0]}")
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    args = context.args or []
    if not slug or not args:
        return await _reply(update, "\U0001f4ce /resume <agent>")

    name = args[0].lower()
    system = _agent_system(slug, name)
    if not system:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        if system == "openfang":
            await openfang.reset_session(kv.get(f"project:{slug}:of_agents:{name}"))
        else:
            await paperclip.resume_agent(kv.get(f"project:{slug}:pc_agents:{name}"))
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
        dash = await paperclip.get_dashboard(company_id) if company_id else {}
    except Exception:
        dash = {}
    try:
        of_agents = await openfang.list_agents()
    except Exception:
        of_agents = []

    pc_count = dash.get("activeAgents", 0)
    await _reply(
        update,
        f"\U0001f4ce Dashboard — {title}\n"
        + "\u2501" * 28
        + f"\n\U0001f4ca Phase:       {phase}"
        f"\n\U0001f3d7 Backbone:   {pc_count} agents (Paperclip)"
        f"\n\U0001f50d Reviewer:   {len(of_agents)} agents (OpenFang)"
        f"\n\U0001f4cb Tasks:       {dash.get('openIssues', 0)} open "
        f"\u2502 {dash.get('doneIssues', 0)} done"
        f"\n\U0001f4b0 Tháng này:   "
        f"${dash.get('monthSpendCents', 0) / 100:.2f}",
    )


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

    name = args[0].lower()
    system = _agent_system(slug, name)
    if not system:
        return await _reply(update, f"\U0001f4ce Agent '{args[0]}' không tồn tại.")

    try:
        if system == "openfang":
            of_id = kv.get(f"project:{slug}:of_agents:{name}")
            await openfang.send_message(of_id, "Wake up — user kicked you. Report status.")
        else:
            pc_id = kv.get(f"project:{slug}:pc_agents:{name}")
            await paperclip.invoke_heartbeat(pc_id)
        await _reply(
            update,
            f"\U0001f4ce \U0001f504 Kicked: {args[0]} — wake invoked",
        )
    except Exception as exc:
        await _reply(update, f"\U0001f4ce Lỗi: {exc}")


# ── /cost ────────────────────────────────────────────────────

async def cmd_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slug = _get_slug(update)
    if not slug:
        return await _reply(update, "\U0001f4ce Không tìm thấy project.")

    company_id = kv.get(f"project:{slug}:company_id")
    lines = ["\U0001f4ce Chi phí tháng này", "\u2501" * 28]

    # Paperclip costs (backbone agents with budget)
    try:
        costs = await paperclip.get_cost_summary(company_id) if company_id else {}
        pc_total = costs.get("totalCents", 0)
        lines.append(f"\U0001f3d7 Backbone:  ${pc_total / 100:.2f}")
    except Exception:
        lines.append("\U0001f3d7 Backbone:  unavailable")

    # OpenFang costs (reviewer agents by tokens)
    try:
        usage = await openfang.get_usage("month")
        by_model = await openfang.get_usage_by_model()
        tokens = usage.get("total_tokens", 0)
        lines.append(f"\U0001f50d Reviewer:  {tokens:,} tokens")
        for m in by_model[:5]:
            mname = m.get("model", "?")
            mtokens = m.get("tokens", 0)
            lines.append(f"   \u2022 {mname}: {mtokens:,}")
    except Exception:
        lines.append("\U0001f50d Reviewer:  unavailable")

    await _reply(update, "\n".join(lines))


# ── utilities ────────────────────────────────────────────────

def _get_slug(update: Update) -> str | None:
    tid = update.message.message_thread_id if update.message else None
    if tid:
        return kv.get(f"topic_to_project:{tid}")
    return None


async def _reply(update: Update, text: str) -> None:
    if update.message:
        await update.message.reply_text(text)
