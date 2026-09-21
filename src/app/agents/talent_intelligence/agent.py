from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from src.app.schemas.agent_response import EmployerResponse, VisualOptions
from src.app.schemas.models import ConversationState, ToolResult

from . import tools
from .graph import TOOL_SCHEMAS, run_tool_loop
from .prompts import SYSTEM_PROMPT
from .registry import build_active_handlers


class TalentIntelligenceAgent:

    system_prompt = SYSTEM_PROMPT

    def __init__(self) -> None:
        self.state = ConversationState()
        self._visual_evidence: list[dict[str, Any]] = []

    def respond_structured(
        self,
        query: str,
        learner_name_or_id: str | None = None,
        visual_options: VisualOptions | None = None,
        history: str | None = None,
    ) -> EmployerResponse:
        """Return text plus optional artifacts; respond() stays text-only."""
        from .visual_delegation import delegate

        if history:
            query = f"{history}\n\nCurrent question:\n{query}"
        markdown = self.respond(query, learner_name_or_id)
        return delegate(query, markdown, self._visual_evidence, visual_options)

    def reset_conversation(self) -> None:
        self.state = ConversationState()

    def respond(self, query: str, learner_name_or_id: str | None = None) -> str:
        """Answer through the LLM tool loop."""
        return self._respond_with_llm(query, learner_name_or_id)

    def respond_with_gemini(
        self, query: str, learner_name_or_id: str | None = None
    ) -> str:
        """Compatibility alias for the LLM-backed answer path."""
        return self._respond_with_llm(query, learner_name_or_id)

    def _respond_with_llm(self, query: str, learner_name_or_id: str | None) -> str:
        self.state.last_tool_calls = []
        self._visual_evidence = []
        failure = self._ensure_learner(query, learner_name_or_id, required=False)
        if failure is not None:
            return failure

        handlers = self._tool_handlers(self.state.active_learner_id)
        answer = run_tool_loop(
            query,
            SYSTEM_PROMPT,
            TOOL_SCHEMAS,
            handlers,
        )
        return self._remember(query, answer)

    def _ensure_learner(
        self,
        query: str,
        learner_name_or_id: str | None,
        required: bool = True,
    ) -> str | None:
        if learner_name_or_id:
            self.state.active_learner_id = None
            profile = self._call(
                "get_learner_profile",
                tools.get_learner_profile,
                learner_name_or_id,
            )
            if profile.status != "ok":
                answer = (
                    self._error_answer()
                    if profile.status == "error"
                    else self._no_learner_answer()
                )
                return self._remember(query, answer)
            self.state.active_learner_id = profile.data["learner_id"]

        if required and not self.state.active_learner_id:
            return self._remember(query, self._no_learner_answer())
        return None

    def _tool_handlers(
        self, learner_id: str | None
    ) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        def invoke(name: str, function: Any, *arguments: Any) -> dict[str, Any]:
            result = self._call(name, function, *arguments)
            return {
                "status": result.status,
                "data": result.data,
                "message": result.message,
            }

        return build_active_handlers(learner_id, invoke)

    def _call(self, name: str, function: Any, *arguments: Any) -> ToolResult:
        try:
            result = function(*arguments)
        except Exception:
            result = ToolResult(
                "error", None, "Evidence retrieval failed. Please retry."
            )
        rows = result.data if isinstance(result.data, list) else []
        if result.status == "ok" and name in {
            "get_skill_proofs",
            "search_evidence",
            "get_behavioral_context",
            "investigate_employer",
        }:
            self._visual_evidence.extend(
                deepcopy(row) for row in rows if isinstance(row, dict)
            )
        self.state.last_tool_calls.append(
            {
                "tool": name,
                "arguments": list(arguments),
                "status": result.status,
                "evidence_ids": [
                    row.get("evidence_id", row.get("event_id")) for row in rows
                ],
            }
        )
        return result

    @staticmethod
    def _error_answer() -> str:
        return (
            "Unable to complete the investigation because evidence retrieval failed. "
            "Please retry. This does not mean that evidence is missing."
        )

    @staticmethod
    def _no_learner_answer() -> str:
        return (
            "Direct conclusion\n- Please provide a learner name or ID to start an investigation.\n\n"  # noqa: E501
            "Uncertainty / gaps\n- Insufficient evidence: no active learner is selected."  # noqa: E501
        )

    def _remember(self, query: str, answer: str) -> str:
        self.state.turns.append({"user": query, "assistant": answer})
        return answer
