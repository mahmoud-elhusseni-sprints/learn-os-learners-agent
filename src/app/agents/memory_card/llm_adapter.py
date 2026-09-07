"""LLM Adapter for calling LLM to extract memory cards using shared agent settings."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .config import MemoryCardAgentConfig
from .prompts import SYSTEM_PROMPT


class MemoryCardLLMAdapter:
    """Encapsulates LLM API calls and JSON extraction using shared agent settings."""

    def __init__(self, config: Optional[MemoryCardAgentConfig] = None) -> None:
        self.config = config or MemoryCardAgentConfig.from_env()

    def generate(self, prompt: str) -> List[Dict[str, Any]]:
        """Call LLM and return parsed JSON list of card dictionaries."""
        api_key = self.config.api_key
        if not api_key:
            raise ValueError(
                "AI_API_KEY is not set.\n"
                "Please configure AI_API_KEY in your environment or .env file."
            )

        raw_text = ""

        # Priority 1: OpenAI-compatible endpoint (LiteLLM, proxy, or OpenAI)
        if self.config.base_url or not self._has_google_genai():
            try:
                from openai import OpenAI

                client_kwargs: Dict[str, Any] = {"api_key": api_key}
                if self.config.base_url:
                    client_kwargs["base_url"] = self.config.base_url

                client = OpenAI(**client_kwargs)
                completion = client.chat.completions.create(
                    model=self.config.model_name,
                    temperature=self.config.temperature,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )
                raw_text = completion.choices[0].message.content or ""
            except Exception as exc:
                if self._has_google_genai():
                    raw_text = self._call_google_genai(api_key, prompt)
                else:
                    raise exc
        else:
            raw_text = self._call_google_genai(api_key, prompt)

        return self.parse_json_response(raw_text)

    def _has_google_genai(self) -> bool:
        try:
            import google.genai  # noqa: F401
            return True
        except ImportError:
            try:
                import google.generativeai  # noqa: F401
                return True
            except ImportError:
                return False

    def _call_google_genai(self, api_key: str, prompt: str) -> str:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=self.config.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=self.config.temperature,
                ),
            )
            return response.text or ""
        except ImportError:
            import google.generativeai as genai_legacy

            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel(
                model_name=self.config.model_name,
                system_instruction=SYSTEM_PROMPT,
            )
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": self.config.temperature,
                    "response_mime_type": "application/json",
                },
            )
            return response.text or ""

    @staticmethod
    def parse_json_response(raw_text: str) -> List[Dict[str, Any]]:
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        if not text:
            return []

        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                for key in ["memory_cards", "cards", "data", "results"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
            return []
        except json.JSONDecodeError as err:
            print(f"  [Warning] Failed to decode JSON from LLM response: {err}")
            return []
