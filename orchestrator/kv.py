"""Lightweight JSON-file KV store for project/topic state."""

import json
from pathlib import Path
from threading import Lock

_KV_PATH = Path("data/kv.json")
_lock = Lock()


def _load() -> dict:
    if _KV_PATH.exists():
        return json.loads(_KV_PATH.read_text(encoding="utf-8"))
    return {}


def _save(data: dict) -> None:
    _KV_PATH.parent.mkdir(parents=True, exist_ok=True)
    _KV_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get(key: str, default=None):
    with _lock:
        return _load().get(key, default)


def set(key: str, value) -> None:
    with _lock:
        data = _load()
        data[key] = value
        _save(data)


def delete(key: str) -> None:
    with _lock:
        data = _load()
        data.pop(key, None)
        _save(data)


def keys(prefix: str = "") -> list[str]:
    with _lock:
        return [k for k in _load() if k.startswith(prefix)]
