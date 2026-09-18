"""Ask the Talent Intelligence Agent one question."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run custom questions against the Talent Intelligence Agent."
    )
    parser.add_argument(
        "--learner",
        help="Learner name or ID for single-learner questions.",
    )
    parser.add_argument(
        "--question",
        help="Question to ask. If omitted, enter one question interactively.",
    )
    args = parser.parse_args()

    from src.app.agents.talent_intelligence.agent import (  # noqa: PLC0415
        TalentIntelligenceAgent,
    )

    question = args.question or input("Question: ").strip()
    if not question:
        print("A question is required.", file=sys.stderr)
        return 2

    agent = TalentIntelligenceAgent()
    print(f"\nQuestion: {question}")
    print(agent.respond(question, learner_name_or_id=args.learner))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
