"""Safe configuration helpers for optional LiteLLM/Gemini use."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_dotenv(path: Path | None = None) -> None:
    """Load only missing variables from a local .env file.

    This small loader avoids requiring python-dotenv and never prints secret
    values. Environment variables supplied by the shell take precedence.
    """
    dotenv_path = path or PROJECT_ROOT / ".env"
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def litellm_settings() -> dict[str, str] | None:
    """Return validated settings without exposing them in logs."""
    load_dotenv()
    names = ("AI_AGENT_URL", "AI_API_KEY", "AI_MODEL")
    values = {name: os.getenv(name, "").strip() for name in names}
    return values if all(values.values()) else None
