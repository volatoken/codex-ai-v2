"""Async client for the OpenFang REST API — Agent execution engine."""

import httpx
from . import config


class OpenFangClient:
    def __init__(self) -> None:
        self.base = config.OPENFANG_URL.rstrip("/")

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if config.OPENFANG_API_KEY:
            h["Authorization"] = f"Bearer {config.OPENFANG_API_KEY}"
        return h

    def _client(self, timeout: int = 300) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base,
            timeout=timeout,
            headers=self._headers(),
        )

    # ── Agents ───────────────────────────────────────────────

    async def spawn_agent(self, manifest_toml: str) -> dict:
        """Spawn a new agent from a TOML manifest string."""
        async with self._client() as c:
            r = await c.post(
                "/api/agents", json={"manifest_toml": manifest_toml}
            )
            r.raise_for_status()
            return r.json()

    async def list_agents(self) -> list[dict]:
        async with self._client(timeout=30) as c:
            r = await c.get("/api/agents")
            r.raise_for_status()
            return r.json()

    async def get_agent(self, agent_id: str) -> dict:
        async with self._client(timeout=30) as c:
            r = await c.get(f"/api/agents/{agent_id}")
            r.raise_for_status()
            return r.json()

    async def kill_agent(self, agent_id: str) -> dict:
        async with self._client() as c:
            r = await c.delete(f"/api/agents/{agent_id}")
            r.raise_for_status()
            return r.json()

    async def update_agent(
        self, agent_id: str, **kwargs
    ) -> dict:
        """Update agent config: description, system_prompt, tags."""
        async with self._client() as c:
            r = await c.put(
                f"/api/agents/{agent_id}/update", json=kwargs
            )
            r.raise_for_status()
            return r.json()

    async def send_message(self, agent_id: str, message: str) -> str:
        """Send a message to an agent and return the response text."""
        async with self._client() as c:
            r = await c.post(
                f"/api/agents/{agent_id}/message",
                json={"message": message},
            )
            r.raise_for_status()
            data = r.json()
            return data["response"]

    async def switch_model(self, agent_id: str, model: str) -> dict:
        async with self._client() as c:
            r = await c.put(
                f"/api/agents/{agent_id}/model",
                json={"model": model},
            )
            r.raise_for_status()
            return r.json()

    async def stop_agent(self, agent_id: str) -> dict:
        async with self._client() as c:
            r = await c.post(f"/api/agents/{agent_id}/stop")
            r.raise_for_status()
            return r.json()

    async def reset_session(self, agent_id: str) -> dict:
        async with self._client() as c:
            r = await c.post(f"/api/agents/{agent_id}/session/reset")
            r.raise_for_status()
            return r.json()

    # ── Models ───────────────────────────────────────────────

    async def list_models(self) -> list[dict]:
        async with self._client(timeout=30) as c:
            r = await c.get("/api/models")
            r.raise_for_status()
            return r.json().get("models", [])

    # ── Usage & Cost ─────────────────────────────────────────

    async def get_usage(self, period: str = "day") -> dict:
        async with self._client(timeout=30) as c:
            r = await c.get("/api/usage", params={"period": period})
            r.raise_for_status()
            return r.json()

    async def get_usage_by_model(self) -> list[dict]:
        async with self._client(timeout=30) as c:
            r = await c.get("/api/usage/by-model")
            r.raise_for_status()
            return r.json().get("models", [])

    # ── KV Memory (per-agent) ────────────────────────────────

    async def kv_get(self, agent_id: str, key: str):
        async with self._client(timeout=30) as c:
            r = await c.get(f"/api/memory/agents/{agent_id}/kv/{key}")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json().get("value")

    async def kv_set(self, agent_id: str, key: str, value) -> None:
        async with self._client(timeout=30) as c:
            r = await c.put(
                f"/api/memory/agents/{agent_id}/kv/{key}",
                json={"value": value},
            )
            r.raise_for_status()

    # ── Provider Configuration ───────────────────────────────

    async def set_provider_key(
        self, provider: str, api_key: str
    ) -> dict:
        async with self._client() as c:
            r = await c.post(
                f"/api/providers/{provider}/key",
                json={"api_key": api_key},
            )
            r.raise_for_status()
            return r.json()

    async def test_provider(self, provider: str) -> dict:
        async with self._client() as c:
            r = await c.post(f"/api/providers/{provider}/test")
            r.raise_for_status()
            return r.json()

    # ── Health & Status ──────────────────────────────────────

    async def health(self) -> dict:
        async with self._client(timeout=10) as c:
            r = await c.get("/api/health")
            r.raise_for_status()
            return r.json()

    async def status(self) -> dict:
        async with self._client(timeout=30) as c:
            r = await c.get("/api/status")
            r.raise_for_status()
            return r.json()
