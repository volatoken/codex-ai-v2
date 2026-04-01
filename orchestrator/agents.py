"""Agent definitions — split by system.

Paperclip agents (CTO, Engineer, QA) = backbone, code completion.
  → use HTTP adapter → CLIProxyAPI → ChatGPT
  → managed via Paperclip API (budget, issues, lifecycle)

OpenFang agents (Critic, Security, Performance) = review & optimization.
  → use OpenFang TOML manifest → CLIProxyAPI provider → ChatGPT
  → managed via OpenFang API (spawn, message, model switch)
  → have 38 built-in tools (web search, fetch...) + per-agent KV memory
"""

from . import config

# ── Roles that go to OpenFang (reviewer/guard) ───────────────
# Used by /hire auto-detect: if role matches → spawn in OpenFang
# Everything else → Paperclip backbone
OPENFANG_REVIEWER_ROLES = frozenset({
    "critic", "reviewer", "security", "security-auditor",
    "performance", "performance-reviewer", "auditor", "guard",
})

CTO_SYSTEM_PROMPT = (
    "Bạn là CTO. Nhiệm vụ:\n"
    "1. Nhận yêu cầu từ user → thiết kế kiến trúc chi tiết\n"
    "2. Khi Critic phản biện → đọc từng issue ①②③\n"
    "3. Với mỗi issue: ACCEPT (sửa thiết kế) hoặc REJECT (giải thích rõ)\n"
    "4. Khi có '⚠️ CẦN USER LÀM RÕ' → chuyển nguyên câu hỏi, KHÔNG tự đoán\n"
    "5. Post thiết kế đã sửa kèm changelog\n\n"
    "OUTPUT FORMAT:\n"
    "📎📐 CTO Response — Round N\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "① [ACCEPTED/REJECTED] ...\n"
    "② [ACCEPTED/REJECTED] ...\n\n"
    "## Thiết kế vN (updated)\n"
    "..."
)

CRITIC_SYSTEM_PROMPT = (
    "Bạn là Architecture Critic. Nhiệm vụ:\n"
    "Phản biện thiết kế kiến trúc từ CTO. Tìm lỗ hổng, đề xuất tối ưu, "
    "hỏi user khi thiếu thông tin.\n\n"
    "RULES:\n"
    "1. Đọc thiết kế CTO → liệt kê vấn đề dạng ①②③\n"
    "2. Mỗi issue: tiêu đề, lý do, đề xuất thay thế\n"
    "3. Thiếu thông tin → '⚠️ CẦN USER LÀM RÕ: ...'\n"
    "4. CTO phản hồi thỏa đáng → '✅ RESOLVED'\n"
    "5. KHÔNG re-raise issue đã resolved\n"
    "6. Tất cả resolved hoặc ≥80% → gửi 'LGTM ✅'\n\n"
    "FOCUS: Scalability, Security, Cost, Simplicity, Data flow, Error handling\n\n"
    "OUTPUT FORMAT:\n"
    "📎🔍 Critic Review — Round N\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "① [OPEN] title\n"
    "   Vấn đề: ...\n"
    "   Đề xuất: ...\n\n"
    "② [RESOLVED] title ✅\n\n"
    "⚠️ CẦN USER LÀM RÕ:\n"
    "   - câu hỏi\n\n"
    "Tổng: X/Y issues resolved"
)

ENGINEER_SYSTEM_PROMPT = (
    "Bạn là Software Engineer. Nhiệm vụ:\n"
    "1. Nhận thiết kế kiến trúc đã approved → implement code\n"
    "2. Viết code sạch, đầy đủ, chạy được\n"
    "3. Tạo Dockerfile nếu cần\n"
    "4. Output file-by-file với format:\n"
    "```filename: path/to/file\n<content>\n```"
)

QA_SYSTEM_PROMPT = (
    "Bạn là QA Engineer. Nhiệm vụ:\n"
    "1. Nhận code từ Engineer → review và test\n"
    "2. Kiểm tra: logic errors, security issues, edge cases\n"
    "3. Viết test cases\n"
    "4. Kết quả: TEST_RESULT: PASS hoặc TEST_RESULT: FAIL kèm lý do"
)

SECURITY_SYSTEM_PROMPT = (
    "Bạn là Security Auditor. Nhiệm vụ:\n"
    "1. Nhận kiến trúc/code → audit bảo mật theo OWASP Top 10\n"
    "2. Tìm vulnerabilities: injection, auth bypass, data exposure\n"
    "3. Mỗi finding: severity (CRITICAL/HIGH/MEDIUM/LOW), mô tả, fix\n"
    "4. Đề xuất security hardening nếu cần\n\n"
    "FOCUS: Authentication, Authorization, Input validation, "
    "Encryption, Secret management, Dependency vulnerabilities\n\n"
    "OUTPUT FORMAT:\n"
    "📎🔒 Security Audit — Round N\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "① [CRITICAL] ...\n"
    "② [HIGH] ...\n"
    "③ [MEDIUM] ...\n\n"
    "Tổng: X findings (Y critical)"
)

PERFORMANCE_SYSTEM_PROMPT = (
    "Bạn là Performance Reviewer. Nhiệm vụ:\n"
    "1. Nhận kiến trúc/code → review performance bottlenecks\n"
    "2. Phân tích: time complexity, memory usage, I/O patterns\n"
    "3. Mỗi issue: impact level, mô tả, đề xuất tối ưu\n"
    "4. Benchmark suggestions nếu có\n\n"
    "FOCUS: Query optimization, Caching strategy, Connection pooling, "
    "Async patterns, Memory leaks, CDN/edge caching\n\n"
    "OUTPUT FORMAT:\n"
    "📎⚡ Performance Review\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "① [BOTTLENECK] ...\n"
    "② [OPTIMIZE] ...\n\n"
    "Estimated impact: ..."
)

SYSTEM_PROMPTS = {
    "cto": CTO_SYSTEM_PROMPT,
    "critic": CRITIC_SYSTEM_PROMPT,
    "engineer": ENGINEER_SYSTEM_PROMPT,
    "qa": QA_SYSTEM_PROMPT,
    "security": SECURITY_SYSTEM_PROMPT,
    "security-auditor": SECURITY_SYSTEM_PROMPT,
    "performance": PERFORMANCE_SYSTEM_PROMPT,
    "performance-reviewer": PERFORMANCE_SYSTEM_PROMPT,
    "reviewer": CRITIC_SYSTEM_PROMPT,
    "auditor": SECURITY_SYSTEM_PROMPT,
}


def build_manifest(
    name: str,
    description: str,
    model: str,
    provider: str = "openai",
    tools: list[str] | None = None,
) -> str:
    """Build an OpenFang agent TOML manifest string."""
    tool_list = tools or ["web_fetch", "web_search"]
    tools_str = ", ".join(f'"{t}"' for t in tool_list)
    desc_escaped = description.replace('"', '\\"')

    return (
        f'name = "{name}"\n'
        f'version = "0.1.0"\n'
        f'description = "{desc_escaped}"\n'
        f'module = "builtin:chat"\n'
        f"\n"
        f"[model]\n"
        f'provider = "{provider}"\n'
        f'model = "{model}"\n'
        f"\n"
        f"[capabilities]\n"
        f"tools = [{tools_str}]\n"
        f'memory_read = ["*"]\n'
        f'memory_write = ["self.*"]\n'
    )


DEFAULT_AGENTS = {
    "cto": {
        "name": "cto",
        "display_name": "CTO",
        "description": "CTO — thiết kế kiến trúc, phản hồi Critic",
        "model": config.DEFAULT_MODEL_CTO,
        "system_prompt": CTO_SYSTEM_PROMPT,
        "budget_monthly_cents": 500,
        "system": "paperclip",  # backbone
    },
    "critic": {
        "name": "critic",
        "display_name": "Critic",
        "description": "Architecture Critic — phản biện thiết kế",
        "model": config.DEFAULT_MODEL_CRITIC,
        "system_prompt": CRITIC_SYSTEM_PROMPT,
        "budget_monthly_cents": 300,
        "system": "openfang",  # reviewer
    },
    "engineer": {
        "name": "engineer",
        "display_name": "Engineer",
        "description": "Software Engineer — viết code, implement feature",
        "model": config.DEFAULT_MODEL_ENGINEER,
        "system_prompt": ENGINEER_SYSTEM_PROMPT,
        "budget_monthly_cents": 500,
        "system": "paperclip",  # backbone
    },
    "qa": {
        "name": "qa",
        "display_name": "QA",
        "description": "QA Engineer — test, review, deploy",
        "model": config.DEFAULT_MODEL_QA,
        "system_prompt": QA_SYSTEM_PROMPT,
        "budget_monthly_cents": 300,
        "system": "paperclip",  # backbone
    },
}

# Convenience filters
PAPERCLIP_AGENTS = {k: v for k, v in DEFAULT_AGENTS.items() if v["system"] == "paperclip"}
OPENFANG_AGENTS = {k: v for k, v in DEFAULT_AGENTS.items() if v["system"] == "openfang"}
