from __future__ import annotations

from collections.abc import Sequence

from langsmith import traceable

from src.app.agents.talent_intelligence.agent import TalentIntelligenceAgent
from src.app.schemas.agent_response import EmployerResponse
from src.app.services.learner_context import learner_directory, resolve_context


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
        self.selection_resolved = False
        self.resolved_selection: str | None = None
        self.preserve_selection = False

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

    @traceable(
        name="talent_conversation",
        process_inputs=lambda inputs: {k: v for k, v in inputs.items() if k != "self"},
    )
    def respond(
        self,
        message: str,
        history: Sequence[dict[str, str]] | None = None,
        learner_name_or_id: str | None = None,
    ) -> EmployerResponse:

        try:
            self.selection_resolved = False
            context = resolve_context(message, learner_name_or_id, learner_directory())
            answer = (
                EmployerResponse(markdown=context.clarification)
                if context.clarification
                else self.agent.respond_structured(
                    message,
                    history=list(history or []),
                    learner_name_or_id=context.active,
                )
            )
            self.resolved_selection = context.saved
            self.preserve_selection = context.preserve_default
            self.selection_resolved = True
            return answer

        except TimeoutError as exc:
            raise AgentTimeoutError("The Talent Intelligence Agent timed out.") from exc

        except Exception as exc:
            raise AgentUpstreamError(
                "The Talent Intelligence Agent could not process the request."
            ) from exc
