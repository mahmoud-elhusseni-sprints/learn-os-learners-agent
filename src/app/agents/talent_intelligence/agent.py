"""Deterministic agent orchestration for the foundational MVP."""

from __future__ import annotations

import re
from typing import Any, Callable

from src.app.models.models import ConversationState, ToolResult

from . import tools
from .graph import TOOL_SCHEMAS, run_tool_loop
from .prompts import SYSTEM_PROMPT

BEHAVIOR_TERMS = (
    "behavior",
    "communication",
    "collaboration",
    "ambiguity",
    "adaptability",
    "blocker",
    "problem solving",
)


class TalentIntelligenceAgent:

    system_prompt = SYSTEM_PROMPT

    def __init__(self) -> None:
        self.state = ConversationState()

    def reset_conversation(self) -> None:
        self.state = ConversationState()

    def respond(self, query: str, learner_name_or_id: str | None = None) -> str:
        self.state.last_tool_calls = []
        failure = self._ensure_learner(query, learner_name_or_id)
        if failure is not None:
            return failure

        lower = query.lower()
        skill = self._extract_skill(lower)
        if skill is not None:
            result = self._call(
                "get_skill_proofs",
                tools.get_skill_proofs,
                self.state.active_learner_id,
                skill,
            )
            answer = self._evidence_answer(skill, result)
        elif any(
            term in lower for term in ("history", "timeline", "milestone", "journey")
        ):
            result = self._call(
                "get_milestone_history",
                tools.get_milestone_history,
                self.state.active_learner_id,
            )
            answer = self._history_answer(result)
        elif any(term in lower for term in ("strength", "gap", "overview")):
            result = self._call(
                "get_strengths_and_gaps",
                tools.get_strengths_and_gaps,
                self.state.active_learner_id,
            )
            answer = self._strengths_answer(result)
        elif any(term in lower for term in BEHAVIOR_TERMS):
            result = self._call(
                "get_behavioral_context",
                tools.get_behavioral_context,
                self.state.active_learner_id,
            )
            answer = self._evidence_answer("behavioral context", result)
        elif any(term in lower for term in ("next step", "next action", "what should")):
            result = self._call(
                "suggest_next_steps",
                tools.suggest_next_steps,
                self.state.active_learner_id,
            )
            answer = self._next_steps_answer(result)
        elif any(
            term in lower for term in ("investigate", "investigation", "employer")
        ):
            result = self._call(
                "investigate_employer",
                tools.investigate_employer,
                self.state.active_learner_id,
                query,
            )
            answer = self._evidence_answer("employer investigation", result)
        else:
            result = self._call(
                "get_learner_profile",
                tools.get_learner_profile,
                self.state.active_learner_id,
            )
            answer = self._profile_answer(result)
        return self._remember(query, answer)

    def respond_with_gemini(
        self, query: str, learner_name_or_id: str | None = None
    ) -> str:
        """Optional Gemini path. Python tools remain the only data source."""
        self.state.last_tool_calls = []
        failure = self._ensure_learner(query, learner_name_or_id)
        if failure is not None:
            return failure

        learner_id = self.state.active_learner_id

        handlers = self._tool_handlers(learner_id)
        answer = run_tool_loop(
            query,
            SYSTEM_PROMPT,
            TOOL_SCHEMAS,
            handlers,
        )
        return self._remember(query, answer)

    def _ensure_learner(self, query: str, learner_name_or_id: str | None) -> str | None:
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

        if not self.state.active_learner_id:
            return self._remember(query, self._no_learner_answer())
        return None

    def _tool_handlers(
        self, learner_id: str
    ) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        def invoke(name: str, function: Any, *arguments: Any) -> dict[str, Any]:
            result = self._call(name, function, *arguments)
            return {
                "status": result.status,
                "data": result.data,
                "message": result.message,
            }

        # Learner ID is controlled in Python; model-provided identities are ignored.
        return {
            "get_learner_profile": lambda _: invoke(
                "get_learner_profile", tools.get_learner_profile, learner_id
            ),
            "get_skill_proofs": lambda args: invoke(
                "get_skill_proofs",
                tools.get_skill_proofs,
                learner_id,
                str(args.get("skill", "")),
            ),
            "get_behavioral_context": lambda _: invoke(
                "get_behavioral_context", tools.get_behavioral_context, learner_id
            ),
            "get_strengths_and_gaps": lambda _: invoke(
                "get_strengths_and_gaps", tools.get_strengths_and_gaps, learner_id
            ),
            "get_milestone_history": lambda _: invoke(
                "get_milestone_history", tools.get_milestone_history, learner_id
            ),
            "investigate_employer": lambda args: invoke(
                "investigate_employer",
                tools.investigate_employer,
                learner_id,
                str(args.get("focus", "")),
            ),
            "suggest_next_steps": lambda _: invoke(
                "suggest_next_steps", tools.suggest_next_steps, learner_id
            ),
        }

    @staticmethod
    def _extract_skill(query: str) -> str | None:
        query = query.lower().strip()
        # A named capability is extracted from the question instead of being
        # limited to a hardcoded skill vocabulary.
        match = re.search(
            r"\b(?:know|with|using|experience in|experience with)\s+"
            r"([a-z0-9+.#-]+(?:\s+[a-z0-9+.#-]+)*)",
            query,
        )
        if match:
            phrase = re.split(
                r"\s+(?:and|or|in|for|during|on|at|based|so)\b", match.group(1)
            )[0]
            return phrase.rstrip(".") or None

        # Covers questions such as "strongest Python contributions" without
        # requiring Python to be registered in this agent.
        match = re.search(
            r"\b(?:strongest|best|recent|relevant)\s+"
            r"([a-z0-9+.#-]+(?:\s+[a-z0-9+.#-]+)*)\s+"
            r"(?:contributions?|experience|work|history)\b",
            query,
        )
        if match:
            return match.group(1).strip()

        match = re.search(
            r"\b(?:their|the learner's|learner's)\s+"
            r"([a-z0-9+.#-]+(?:\s+[a-z0-9+.#-]+)*)\s+"
            r"(?:history|experience)\b",
            query,
        )
        if match:
            return match.group(1).strip()
        return None

    def _call(self, name: str, function: Any, *arguments: Any) -> ToolResult:
        try:
            result = function(*arguments)
        except Exception:
            # Do not expose exception text, local paths, or credentials.
            result = ToolResult(
                "error", None, "Evidence retrieval failed. Please retry."
            )
        rows = result.data if isinstance(result.data, list) else []
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
    def _evidence_lines(items: list[dict[str, Any]]) -> str:
        return "\n".join(
            f"- [{item['evidence_id']}] {item['source_type']} "
            f"— {item.get('date') or 'unknown date'}: "
            f"{item['observation']} Context: {item['context']}"
            for item in items
        )

    def _evidence_answer(self, subject: str, result: ToolResult) -> str:
        if result.status == "error":
            return self._error_answer()
        items = result.data if isinstance(result.data, list) else []
        if not items:
            return self._insufficient_answer(subject)
        most_recent = max((item.get("date") or "unknown" for item in items))
        return (
            f"Direct conclusion\n- Partial evidence is available for {subject}.\n\n"
            f"Observed evidence\n{self._evidence_lines(items)}\n\n"
            "Interpretation\n- The cited observations support only the specific contexts "  # noqa: E501
            "described; they do not establish a permanent trait or hiring decision.\n\n"
            f"Recency and coverage\n- Most recent relevant evidence: {most_recent}.\n"
            f"- Evidence coverage: {len(items)} record(s).\n\n"
            "Uncertainty / gaps\n- Evidence is limited to the cited records."
        )

    def _history_answer(self, result: ToolResult) -> str:
        if result.status == "error":
            return self._error_answer()
        items = result.data if isinstance(result.data, list) else []
        if not items:
            return self._insufficient_answer("milestone history")
        lines = "\n".join(
            f"- [{item['event_id']}] interaction_log — {item.get('date')}: "
            f"{item['summary']}"
            for item in items
        )
        return (
            "Direct conclusion\n- The following recorded learner milestones are available.\n\n"  # noqa: E501
            f"Observed evidence\n{lines}\n\n"
            "Interpretation\n- This is a timeline of recorded workflow events, "
            "not a complete capability assessment.\n\n"
            f"Recency and coverage\n- Most recent milestone: {items[-1].get('date') or 'unknown'}.\n"  # noqa: E501
            f"- Evidence coverage: {len(items)} event(s).\n\n"
            "Uncertainty / gaps\n- Insufficient evidence for events that are not present in the records."  # noqa: E501
        )

    def _strengths_answer(self, result: ToolResult) -> str:
        if result.status == "error":
            return self._error_answer()
        data = (
            result.data
            if isinstance(result.data, dict)
            else {"strengths": [], "gaps": []}
        )
        strengths = data.get("strengths", [])
        gaps = data.get("gaps", [])
        if not strengths:
            return self._insufficient_answer("strengths and gaps")
        evidence = "\n".join(
            f"- [{item['evidence_ids'][0]}] {item['source_type']} "
            f"— {item.get('most_recent_date') or 'unknown date'}: "
            f"{item['area']}: {item['observation']}"
            for item in strengths
        )
        gap_lines = (
            "\n".join(
                f"- {item['area']}: Insufficient evidence. {item['reason']}"
                for item in gaps
            )
            or "- No predefined coverage gaps."
        )
        return (
            "Direct conclusion\n- The records show observed areas alongside explicit coverage gaps.\n\n"  # noqa: E501
            f"Observed evidence\n{evidence}\n\n"
            "Interpretation\n- These are record-level observations, "
            "not an overall ranking or hiring recommendation.\n\n"
            f"Recency and coverage\n- Evidence coverage: {len(strengths)} observed record(s).\n\n"  # noqa: E501
            f"Uncertainty / gaps\n{gap_lines}"
        )

    def _next_steps_answer(self, result: ToolResult) -> str:
        if result.status == "error":
            return self._error_answer()
        items = result.data if isinstance(result.data, list) else []
        if not items:
            return self._insufficient_answer("next steps")
        lines = "\n".join(
            f"- {item['area']}: {item['action']} ({item['reason']})" for item in items
        )
        return (
            "Direct conclusion\n- Additional evidence-gathering steps are "
            "available.\n\n"
            f"Observed evidence\n{lines}\n\n"
            "Interpretation\n- These actions address coverage gaps; they are "
            "not hiring recommendations.\n\n"
            "Uncertainty / gaps\n- The suggested steps do not establish "
            "capability until new evidence is recorded."
        )

    @staticmethod
    def _profile_answer(result: ToolResult) -> str:
        if result.status == "error":
            return TalentIntelligenceAgent._error_answer()
        if result.status != "ok":
            return TalentIntelligenceAgent._no_learner_answer()
        profile = result.data
        coverage = profile["evidence_coverage"]
        return (
            f"Direct conclusion\n- {profile['name']} has an available learner profile.\n\n"  # noqa: E501
            f"Observed evidence\n- Profile record: {profile.get('group_name')} "
            f"({profile.get('round_name')}).\n\n"
            "Interpretation\n- This is profile context, not a capability assessment.\n\n"  # noqa: E501
            "Recency and coverage\n"
            f"- Most recent relevant evidence: {coverage['most_recent_evidence_date'] or 'unknown'}.\n"  # noqa: E501
            f"- Evidence coverage: {coverage['evidence_count']} record(s).\n\n"
            "Uncertainty / gaps\n- Insufficient evidence for skills not specifically retrieved."  # noqa: E501
        )

    @staticmethod
    def _error_answer() -> str:
        return (
            "Unable to complete the investigation because evidence retrieval failed. "
            "Please retry. This does not mean that evidence is missing."
        )

    @staticmethod
    def _insufficient_answer(subject: str) -> str:
        return (
            f"Direct conclusion\n- Insufficient evidence to assess {subject}.\n\n"
            "Observed evidence\n- No matching evidence records were returned.\n\n"
            "Interpretation\n- Missing records do not prove that the learner lacks this skill or behavior.\n\n"  # noqa: E501
            "Recency and coverage\n- Most recent relevant evidence: unknown.\n"
            "- Evidence coverage: 0 records.\n\n"
            "Uncertainty / gaps\n- Insufficient evidence."
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
