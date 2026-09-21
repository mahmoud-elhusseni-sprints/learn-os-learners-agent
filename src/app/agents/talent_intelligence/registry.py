from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.app.schemas.models import ToolResult

from . import tools

ToolFunction = Callable[..., ToolResult]
Invoke = Callable[..., dict[str, Any]]
MISSING_LEARNER = {
    "status": "error",
    "data": None,
    "message": "A learner name or ID is required for this tool.",
}

TOOL_FUNCTIONS: dict[str, ToolFunction] = {
    "get_learner_profile": tools.get_learner_profile,
    "compare_learners": tools.compare_learners,
    "get_skill_proofs": tools.get_skill_proofs,
    "search_evidence": tools.search_evidence,
    "get_review_outcomes": tools.get_review_outcomes,
    "get_assessment_results": tools.get_assessment_results,
    "find_learners_with_skill": tools.find_learners_with_skill,
    "get_behavioral_context": tools.get_behavioral_context,
    "get_strengths_and_gaps": tools.get_strengths_and_gaps,
    "get_milestone_history": tools.get_milestone_history,
    "investigate_employer": tools.investigate_employer,
    "suggest_next_steps": tools.suggest_next_steps,
}

_LEARNER_ID_PARAM: dict[str, Any] = {
    "type": "string",
    "description": (
        "Optional learner name or ID. Defaults to active learner if omitted."
    ),
}

TOOL_METADATA: dict[str, dict[str, Any]] = {
    "get_learner_profile": {
        "description": (
            "Retrieve profile context for the active learner or a specified learner."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "learner_id": _LEARNER_ID_PARAM,
            },
        },
    },
    "compare_learners": {
        "description": (
            "Compare two named learners by evidence coverage and cited records. "
            "Do not rank suitability or infer skill from missing evidence."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "first_learner": {"type": "string"},
                "second_learner": {"type": "string"},
                "focus": {"type": "string"},
            },
            "required": ["first_learner", "second_learner"],
        },
    },
    "get_skill_proofs": {
        "description": (
            "Retrieve evidence for one named skill of the active learner or "
            "a specified learner."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill": {"type": "string"},
                "learner_id": _LEARNER_ID_PARAM,
            },
            "required": ["skill"],
        },
    },
    "search_evidence": {
        "description": (
            "Search evidence for the active learner or a specified learner "
            "with optional filters."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "source_type": {"type": "string"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "learner_id": _LEARNER_ID_PARAM,
            },
        },
    },
    "get_review_outcomes": {
        "description": (
            "Retrieve submissions, verdicts, feedback, and rubric outcomes "
            "for the active or specified learner."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "learner_id": _LEARNER_ID_PARAM,
            },
        },
    },
    "get_assessment_results": {
        "description": (
            "Retrieve assessment scores and question-level results for the "
            "active or specified learner."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "learner_id": _LEARNER_ID_PARAM,
            },
        },
    },
    "find_learners_with_skill": {
        "description": (
            "Find learners with evidence for a named skill and summarize the "
            "supporting records. This orders evidence coverage only; it does "
            "not determine who is best."
        ),
        "parameters": {
            "type": "object",
            "properties": {"skill": {"type": "string"}},
            "required": ["skill"],
        },
    },
    "get_behavioral_context": {
        "description": (
            "Retrieve contextual behavioral observations for the active "
            "or specified learner."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "learner_id": _LEARNER_ID_PARAM,
            },
        },
    },
    "get_strengths_and_gaps": {
        "description": (
            "Retrieve observed areas and evidence gaps for the active or "
            "specified learner."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "learner_id": _LEARNER_ID_PARAM,
            },
        },
    },
    "get_milestone_history": {
        "description": (
            "Retrieve chronological learner milestones for the active or "
            "specified learner."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "learner_id": _LEARNER_ID_PARAM,
            },
        },
    },
    "investigate_employer": {
        "description": (
            "Retrieve graph evidence relevant to an employer investigation "
            "for the active or specified learner."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "focus": {"type": "string"},
                "learner_id": _LEARNER_ID_PARAM,
            },
        },
    },
    "suggest_next_steps": {
        "description": (
            "Suggest evidence-gathering next steps from coverage gaps for "
            "the active or specified learner."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "learner_id": _LEARNER_ID_PARAM,
            },
        },
    },
}


def build_tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {"name": name, **metadata},
        }
        for name, metadata in TOOL_METADATA.items()
    ]


def build_active_handlers(
    learner_id: str | None, invoke: Invoke
) -> dict[str, Callable[[dict[str, Any]], Any]]:
    def resolve_target(args: dict[str, Any]) -> str | None:
        target = args.get("learner_id") or learner_id
        if not target:
            return None
        target_str = str(target).strip()
        learner = tools._find_learner(target_str)
        if learner and learner.get("learner_id"):
            return str(learner["learner_id"])
        return target_str

    def learner_handler(
        name: str, arguments: tuple[Any, ...] = ()
    ) -> Callable[[dict[str, Any]], Any]:
        def handle(args: dict[str, Any]) -> Any:
            target = resolve_target(args)
            if not target:
                return dict(MISSING_LEARNER)
            fn = getattr(tools, name, TOOL_FUNCTIONS[name])
            return invoke(name, fn, target, *arguments)

        return handle

    def learner_args_handler(
        name: str,
        arguments: Callable[[dict[str, Any]], tuple[Any, ...]],
    ) -> Callable[[dict[str, Any]], Any]:
        def handle(args: dict[str, Any]) -> Any:
            target = resolve_target(args)
            if not target:
                return dict(MISSING_LEARNER)
            fn = getattr(tools, name, TOOL_FUNCTIONS[name])
            return invoke(name, fn, target, *arguments(args))

        return handle

    return {
        "get_learner_profile": learner_handler("get_learner_profile"),
        "compare_learners": lambda args: invoke(
            "compare_learners",
            getattr(tools, "compare_learners", TOOL_FUNCTIONS["compare_learners"]),
            str(args.get("first_learner", "")),
            str(args.get("second_learner", "")),
            str(args.get("focus", "")),
        ),
        "get_skill_proofs": learner_args_handler(
            "get_skill_proofs",
            lambda args: (str(args.get("skill", "")),),
        ),
        "search_evidence": learner_args_handler(
            "search_evidence",
            lambda args: (
                str(args.get("query", "")),
                str(args.get("source_type", "")),
                str(args.get("start_date", "")),
                str(args.get("end_date", "")),
                int(args.get("limit", 100)),
            ),
        ),
        "get_review_outcomes": learner_handler("get_review_outcomes"),
        "get_assessment_results": learner_handler("get_assessment_results"),
        "find_learners_with_skill": lambda args: invoke(
            "find_learners_with_skill",
            getattr(
                tools,
                "find_learners_with_skill",
                TOOL_FUNCTIONS["find_learners_with_skill"],
            ),
            str(args.get("skill", "")),
        ),
        "get_behavioral_context": learner_handler("get_behavioral_context"),
        "get_strengths_and_gaps": learner_handler("get_strengths_and_gaps"),
        "get_milestone_history": learner_handler("get_milestone_history"),
        "investigate_employer": learner_args_handler(
            "investigate_employer",
            lambda args: (str(args.get("focus", "")),),
        ),
        "suggest_next_steps": learner_handler("suggest_next_steps"),
    }


__all__ = [
    "TOOL_FUNCTIONS",
    "TOOL_METADATA",
    "build_active_handlers",
    "build_tool_schemas",
]
