from __future__ import annotations

from collections.abc import Sequence

from src.app.agents.talent_intelligence.agent import TalentIntelligenceAgent
from src.app.schemas.agent_response import EmployerResponse

class AgentOrchestrationError(Exception):
    """Base exception for agent orchestration failures."""


class AgentTimeoutError(AgentOrchestrationError):
    """Raised when the agent exceeds its execution timeout."""


class AgentUpstreamError(AgentOrchestrationError):
    """Raised when the agent or its graph dependencies fail."""


class AgentOrchestrationAdapter:
    """Application-facing adapter around the Talent Intelligence Agent."""

    def __init__(self, agent: TalentIntelligenceAgent | None = None) -> None:
        self.agent = agent or TalentIntelligenceAgent()

    @staticmethod
    def format_history(history: Sequence[dict[str, str]]) -> str:
        """Format persisted conversation history for future agent use."""

        if not history:
            return ""

        lines = ["Previous conversation:"]

        for message in history:
            role = message["role"].capitalize()
            content = message["content"]
            lines.append(f"{role}: {content}")

        return "\n".join(lines)
    
    def respond(
        self,
        message: str,
        history: Sequence[dict[str, str]] | None = None,
        learner_name_or_id: str | None = None,
    ) -> EmployerResponse:
        """Run the Talent Intelligence Agent and return its structured response."""
    
        try:
            return self.agent.respond_structured(
                message,
                learner_name_or_id=learner_name_or_id,
            )
        except TimeoutError as exc:
            raise AgentTimeoutError(
                "The Talent Intelligence Agent timed out."
            ) from exc
        except Exception as exc:
            raise AgentUpstreamError(
                "The Talent Intelligence Agent could not process the request."
            ) from exc