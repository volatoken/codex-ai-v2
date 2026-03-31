"""CLIProxyAPI client — OpenAI-compatible chat completions."""

import httpx
from . import config


async def chat(
    model: str,
    messages: list[dict],
    api_key: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Send a chat completion request and return the assistant message."""
    key = api_key or config.CLIPROXY_OPENFANG_KEY
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{config.CLIPROXY_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def list_models(api_key: str | None = None) -> list[str]:
    """List available model IDs from CLIProxyAPI."""
    key = api_key or config.CLIPROXY_OPENFANG_KEY
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{config.CLIPROXY_URL}/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return sorted(m["id"] for m in data.get("data", []))
