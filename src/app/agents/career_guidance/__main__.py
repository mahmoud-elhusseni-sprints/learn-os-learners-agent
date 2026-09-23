"""Run the Career Guidance Agent on a JSON profile.

    python -m src.app.agents.career_guidance docs/examples/career_guidance_request.json
    python -m src.app.agents.career_guidance request.json --llm

Without ``--llm`` the result is fully deterministic and needs no API key.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.app.schemas.career_guidance import CareerGuidanceProfile

from .agent import CareerGuidanceAgent, CareerGuidanceError, LLMRecommendationWriter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("profile", type=Path, help="Path to a profile JSON file.")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Word recommendations with the configured LLM (needs AI_* settings).",
    )
    args = parser.parse_args(argv)

    try:
        profile = CareerGuidanceProfile.model_validate(
            json.loads(args.profile.read_text(encoding="utf-8"))
        )
        writer = LLMRecommendationWriter.from_env() if args.llm else None
        result = CareerGuidanceAgent(writer=writer).analyze(profile)
    except (CareerGuidanceError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
