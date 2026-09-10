"""Optional LiteLLM/Gemini structured-output adapter; no persistence access."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

from dotenv import dotenv_values
from openai import OpenAI
from openai.types.shared_params import ResponseFormatJSONSchema

from src.app.models.models import MemoryCard, MetricDraft, ProfileMetric

from .agent import ProfileUpdateError
from .prompts import SYSTEM_PROMPT, build_metric_input


class LiteLLMMetricSynthesizer:
    """Use the configured model with JSON schema and mandatory local validation."""

    def __init__(self, client: Any, model: str) -> None:
        self.client = client
        self.model = model

    @classmethod
    def from_env(cls, env_path: Path | None = None) -> LiteLLMMetricSynthesizer:
        """Read existing AI_* settings without printing secrets or mutating env."""
        path = env_path or Path(__file__).resolve().parents[4] / ".env"
        values = {**dotenv_values(path), **os.environ}
        names = ("AI_AGENT_URL", "AI_API_KEY", "AI_MODEL")
        if any(not values.get(name) for name in names):
            raise ProfileUpdateError("Configure AI_AGENT_URL, AI_API_KEY and AI_MODEL.")
        client = OpenAI(
            base_url=str(values["AI_AGENT_URL"]),
            api_key=str(values["AI_API_KEY"]),
            timeout=45.0,
            max_retries=1,
        )
        return cls(client, str(values["AI_MODEL"]))

    def synthesize(
        self,
        metric_key: str,
        previous: ProfileMetric | None,
        cards: list[MemoryCard],
    ) -> MetricDraft:
        """Fail closed on API errors, refusals, truncation or invalid JSON."""
        response_format = cast(
            ResponseFormatJSONSchema,
            {
                "type": "json_schema",
                "json_schema": {
                    "name": "metric_update",
                    "strict": True,
                    "schema": MetricDraft.model_json_schema(),
                },
            },
        )
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_metric_input(metric_key, previous, cards),
                    },
                ],
                response_format=response_format,
            )
            choice = completion.choices[0]
            if choice.finish_reason != "stop" or choice.message.refusal:
                raise ValueError("Incomplete or refused response")
            return MetricDraft.model_validate_json(choice.message.content or "")
        except Exception:
            raise ProfileUpdateError(
                "Model request failed or returned an invalid metric update."
            ) from None
