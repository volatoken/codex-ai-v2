"""Async client for the Paperclip REST API — project management backbone.

Paperclip manages agent definitions (HTTP adapter → CLIProxyAPI → ChatGPT),
issues, projects, budgets.  The invoke_agent() method reads the agent's
adapter config from Paperclip and makes the actual LLM call through it,
so Paperclip is the single source of truth for model, system prompt, budget.
"""

import httpx
from . import config


def make_agent_config(
    system_prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    """Build Paperclip adapterConfig that routes through CLIProxyAPI."""
    return {
        "url": f"{config.CLIPROXY_URL}/v1/chat/completions",
        "headers": {
            "Authorization": f"Bearer {config.CLIPROXY_API_KEY}",
            "Content-Type": "application/json",
        },
        "payloadTemplate": {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
            ],
        },
    }


class PaperclipClient:
    def __init__(self) -> None:
        self.base = config.PAPERCLIP_URL.rstrip("/")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base,
            timeout=30,
            headers={"Content-Type": "application/json"},
        )

    # ── Companies ────────────────────────────────────────────

    async def create_company(self, name: str, description: str = "") -> dict:
        async with self._client() as c:
            r = await c.post(
                "/api/companies", json={"name": name, "description": description}
            )
            r.raise_for_status()
            return r.json()

    async def get_companies(self) -> list[dict]:
        async with self._client() as c:
            r = await c.get("/api/companies")
            r.raise_for_status()
            return r.json()

    async def get_dashboard(self, company_id: str) -> dict:
        async with self._client() as c:
            r = await c.get(f"/api/companies/{company_id}/dashboard")
            r.raise_for_status()
            return r.json()

    # ── Agents ───────────────────────────────────────────────

    async def create_agent(self, company_id: str, agent_data: dict) -> dict:
        async with self._client() as c:
            r = await c.post(
                f"/api/companies/{company_id}/agents", json=agent_data
            )
            r.raise_for_status()
            return r.json()

    async def get_agents(self, company_id: str) -> list[dict]:
        async with self._client() as c:
            r = await c.get(f"/api/companies/{company_id}/agents")
            r.raise_for_status()
            return r.json()

    async def update_agent(self, agent_id: str, data: dict) -> dict:
        async with self._client() as c:
            r = await c.patch(f"/api/agents/{agent_id}", json=data)
            r.raise_for_status()
            return r.json()

    async def pause_agent(self, agent_id: str) -> dict:
        async with self._client() as c:
            r = await c.post(f"/api/agents/{agent_id}/pause")
            r.raise_for_status()
            return r.json()

    async def resume_agent(self, agent_id: str) -> dict:
        async with self._client() as c:
            r = await c.post(f"/api/agents/{agent_id}/resume")
            r.raise_for_status()
            return r.json()

    async def terminate_agent(self, agent_id: str) -> dict:
        async with self._client() as c:
            r = await c.post(f"/api/agents/{agent_id}/terminate")
            r.raise_for_status()
            return r.json()

    async def invoke_heartbeat(self, agent_id: str) -> dict:
        async with self._client() as c:
            r = await c.post(f"/api/agents/{agent_id}/heartbeat/invoke")
            r.raise_for_status()
            return r.json()

    # ── Issues ───────────────────────────────────────────────

    async def create_issue(self, company_id: str, issue_data: dict) -> dict:
        async with self._client() as c:
            r = await c.post(
                f"/api/companies/{company_id}/issues", json=issue_data
            )
            r.raise_for_status()
            return r.json()

    async def get_issues(self, company_id: str, **params) -> list[dict]:
        async with self._client() as c:
            r = await c.get(f"/api/companies/{company_id}/issues", params=params)
            r.raise_for_status()
            return r.json()

    async def update_issue(self, issue_id: str, data: dict) -> dict:
        async with self._client() as c:
            r = await c.patch(f"/api/issues/{issue_id}", json=data)
            r.raise_for_status()
            return r.json()

    async def checkout_issue(self, issue_id: str, agent_id: str) -> dict:
        async with self._client() as c:
            r = await c.post(
                f"/api/issues/{issue_id}/checkout",
                json={
                    "agentId": agent_id,
                    "expectedStatuses": ["todo", "backlog", "blocked"],
                },
            )
            r.raise_for_status()
            return r.json()

    async def add_comment(
        self, issue_id: str, body: str, agent_id: str | None = None
    ) -> dict:
        async with self._client() as c:
            payload: dict = {"body": body}
            if agent_id:
                payload["authorAgentId"] = agent_id
            r = await c.post(f"/api/issues/{issue_id}/comments", json=payload)
            r.raise_for_status()
            return r.json()

    # ── Projects ─────────────────────────────────────────────

    async def create_project(self, company_id: str, project_data: dict) -> dict:
        async with self._client() as c:
            r = await c.post(
                f"/api/companies/{company_id}/projects", json=project_data
            )
            r.raise_for_status()
            return r.json()

    async def get_projects(self, company_id: str) -> list[dict]:
        async with self._client() as c:
            r = await c.get(f"/api/companies/{company_id}/projects")
            r.raise_for_status()
            return r.json()

    # ── Goals ────────────────────────────────────────────────

    async def create_goal(self, company_id: str, goal_data: dict) -> dict:
        async with self._client() as c:
            r = await c.post(
                f"/api/companies/{company_id}/goals", json=goal_data
            )
            r.raise_for_status()
            return r.json()

    # ── Costs & Budgets ──────────────────────────────────────

    async def get_cost_summary(self, company_id: str) -> dict:
        async with self._client() as c:
            r = await c.get(f"/api/companies/{company_id}/costs/summary")
            r.raise_for_status()
            return r.json()

    async def set_agent_budget(self, agent_id: str, monthly_cents: int) -> dict:
        async with self._client() as c:
            r = await c.patch(
                f"/api/agents/{agent_id}/budgets",
                json={"budgetMonthlyCents": monthly_cents},
            )
            r.raise_for_status()
            return r.json()

    async def invoke_agent(self, agent_id: str, message: str) -> str:
        """Send a message to a Paperclip agent via its HTTP adapter.

        Reads the agent's adapterConfig from Paperclip, appends the user
        message to the payload template, calls the configured LLM endpoint
        (CLIProxyAPI), and returns the assistant response.
        Paperclip stays the source of truth for model, prompt, and budget.
        """
        # 1. Get agent config from Paperclip
        async with self._client() as c:
            r = await c.get(f"/api/agents/{agent_id}")
            r.raise_for_status()
            agent = r.json()

        ac = agent.get("adapterConfig", agent.get("adapter_config", {}))
        url = ac.get("url", f"{config.CLIPROXY_URL}/v1/chat/completions")
        headers = ac.get("headers", {
            "Authorization": f"Bearer {config.CLIPROXY_API_KEY}",
            "Content-Type": "application/json",
        })
        payload = dict(ac.get("payloadTemplate", {}))

        # 2. Append user message to the conversation
        messages = list(payload.get("messages", []))
        messages.append({"role": "user", "content": message})
        payload["messages"] = messages

        # 3. Call LLM via the agent's configured endpoint
        async with httpx.AsyncClient(timeout=300) as c:
            r = await c.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
