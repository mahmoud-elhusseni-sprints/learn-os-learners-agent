"""Explicit local CLI: validation is offline; synthesis requires --live."""

import argparse
from pathlib import Path

from pydantic import ValidationError

from .agent import LearnerProfileUpdateAgent, ProfileUpdateError
from .models import ProfileUpdateInput


def main() -> int:
    """Validate a request file, or explicitly send it to the configured model."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Task 10 request JSON path")
    parser.add_argument("--live", action="store_true", help="Call LiteLLM/Gemini")
    args = parser.parse_args()
    try:
        request = ProfileUpdateInput.model_validate_json(
            args.input.read_text(encoding="utf-8")
        )
        if not args.live:
            print("Input valid. No model call made; use --live to synthesize.")
            return 0
        from .llm_adapter import LiteLLMMetricSynthesizer

        agent = LearnerProfileUpdateAgent(LiteLLMMetricSynthesizer.from_env())
        print(agent.update(request).model_dump_json(indent=2))
        return 0
    except (OSError, ValidationError, ProfileUpdateError):
        print(
            "Profile update failed. Check input, configuration and model availability."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
