"""Async client for the Paperclip REST API."""

import httpx
from . import config


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
