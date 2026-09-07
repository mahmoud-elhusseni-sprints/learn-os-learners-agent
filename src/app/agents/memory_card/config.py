"""Configuration and environment settings for Memory Card Agent.

Uses the same API key and configuration settings (AI_API_KEY, AI_AGENT_URL, AI_MODEL)
shared across the agents in src/app/agents.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def load_dotenv(path: Path | None = None) -> None:
    """Load only missing variables from a local .env file."""
    dotenv_path = path or PROJECT_ROOT / ".env"
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class MemoryCardAgentConfig:
    """Runtime configuration for MemoryCardAgent sharing agent settings."""

    api_key: str = ""
    base_url: Optional[str] = None
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> MemoryCardAgentConfig:
        load_dotenv()
        # Same API key used by the other agents in src/app/agents
        api_key = (
            os.getenv("AI_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("OPENAI_API_KEY", "")
        ).strip()
        base_url = os.getenv("AI_AGENT_URL", "").strip() or None
        model_name = (
            os.getenv("AI_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        ).strip()
        return cls(api_key=api_key, base_url=base_url, model_name=model_name)
