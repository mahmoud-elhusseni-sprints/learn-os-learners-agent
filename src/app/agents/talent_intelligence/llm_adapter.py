"""Optional OpenAI-compatible LiteLLM/Gemini adapter.

The deterministic agent remains the tested local fallback. This adapter is
separate so a model/provider issue cannot change retrieval tool contracts.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from .config import litellm_settings
from .prompts import SYSTEM_PROMPT


class LiteLLMGeminiAdapter:
    """Generate a grounded final response from already retrieved evidence.

    The adapter intentionally does not get filesystem access and is given only
    tool results produced by the Python retrieval layer.
    """

    def __init__(self) -> None:
        settings = litellm_settings()
        if settings is None:
            raise RuntimeError(
                "LiteLLM is not configured. Add all values to the root .env file."
            )
        self._settings = settings

    def generate_grounded_answer(
        self, question: str, tool_results: list[dict[str, Any]]
    ) -> str:
        """Call an OpenAI-compatible LiteLLM chat-completions endpoint.

        This is used only after a deterministic tool call; therefore the model
        can phrase an answer but cannot retrieve extra learner data.
        """
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError(
                "Install optional dependencies with: pip install -r requirements.txt"
            ) from error

        client = OpenAI(
            base_url=self._settings["AI_AGENT_URL"],
            api_key=self._settings["AI_API_KEY"],
        )
        completion = client.chat.completions.create(
            model=self._settings["AI_MODEL"],
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Employer question: {question}\n\n"
                        "Approved tool results (the only learner-specific evidence you may use):\n"  # noqa: E501
                        f"{tool_results}"
                    ),
                },
            ],
        )
        return completion.choices[0].message.content or "Insufficient evidence"

    def run_tool_loop(
        self,
        question: str,
        tool_handlers: dict[str, Callable[[dict[str, Any]], Any]],
    ) -> str:
        """Let Gemini choose a tool while Python retains retrieval control."""
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError(
                "Install optional dependencies with: pip install -r requirements.txt"
            ) from error

        client = OpenAI(
            base_url=self._settings["AI_AGENT_URL"],
            api_key=self._settings["AI_API_KEY"],
        )
        tools = [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            }
            for name, description, parameters in (
                (
                    "get_learner_profile",
                    "Retrieve profile context for the active learner.",
                    {"type": "object", "properties": {}},
                ),
                (
                    "get_skill_proofs",
                    "Retrieve evidence for one named skill of the active learner.",
                    {
                        "type": "object",
                        "properties": {"skill": {"type": "string"}},
                        "required": ["skill"],
                    },
                ),
                (
                    "get_behavioral_context",
                    "Retrieve contextual behavioral observations for the active learner.",  # noqa: E501
                    {"type": "object", "properties": {}},
                ),
                (
                    "get_strengths_and_gaps",
                    "Retrieve evidence-backed observed areas and evidence gaps for the active learner.",  # noqa: E501
                    {"type": "object", "properties": {}},
                ),
                (
                    "get_milestone_history",
                    "Retrieve chronological submission, feedback, and outcome milestones for the active learner.",  # noqa: E501
                    {"type": "object", "properties": {}},
                ),
            )
        ]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        for _ in range(3):
            completion = client.chat.completions.create(
                model=self._settings["AI_MODEL"],
                temperature=0,
                messages=messages,
                tools=tools,  # type: ignore[call-overload]
                tool_choice="auto",
            )
            message = completion.choices[0].message
            tool_calls = message.tool_calls or []
            messages.append(message.model_dump(exclude_none=True))
            if not tool_calls:
                return message.content or "Insufficient evidence"  # noqa: E501
            for call in tool_calls:
                try:
                    arguments = json.loads(
                        call.function.arguments or "{}"
                    )  # noqa: E501
                except json.JSONDecodeError:
                    arguments = {}
                handler = tool_handlers.get(call.function.name)
                output = (
                    handler(arguments)
                    if handler
                    else {"status": "error", "message": "Unknown tool."}  # noqa: E501
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(output, ensure_ascii=False, default=str),
                    }
                )
        return "Insufficient evidence"
