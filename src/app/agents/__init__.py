"""Agents package for learn-os-learners-agent."""

from importlib import import_module
from typing import Any

__all__ = [
    "MemoryCardAgent",
    "TalentIntelligenceAgent",
]


def __getattr__(name: str) -> Any:
    if name == "MemoryCardAgent":
        return import_module("src.app.agents.memory_card").MemoryCardAgent
    if name == "TalentIntelligenceAgent":
        return import_module(
            "src.app.agents.talent_intelligence.agent"
        ).TalentIntelligenceAgent
    raise AttributeError(name)
