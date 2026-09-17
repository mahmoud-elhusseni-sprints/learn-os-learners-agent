"""Run the preprocessing and memory-card extraction pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run learner preprocessing, evidence extraction, and memory-card "
            "generation."
        )
    )
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Use the optional LMS and mentor LLM agents during preprocessing.",
    )
    args = parser.parse_args()

    from src.app.core.config import (  # noqa: PLC0415
        DATASOURCE_OUTPUT_FILE,
        MEMORY_CARDS_OUTPUT_FILE,
        PROFILES_OUTPUT_FILE,
        RUBRICS_OUTPUT_FILE,
    )
    from src.app.ingestion.pipeline import run_pipeline  # noqa: PLC0415

    result = run_pipeline(run_llm_agents=args.with_llm)
    outputs = {
        "learner profiles": (PROFILES_OUTPUT_FILE, result["profiles"]),
        "data sources": (DATASOURCE_OUTPUT_FILE, result["datasources"]),
        "memory cards": (MEMORY_CARDS_OUTPUT_FILE, result["memory_cards"]),
        "mentor rubrics": (RUBRICS_OUTPUT_FILE, None),
    }

    print("\nPreprocessing test completed.")
    for name, (path, records) in outputs.items():
        state = "created" if Path(path).exists() else "missing"
        count = f" ({len(records)} records)" if records is not None else ""
        print(f"- {name}: {state}{count} -> {path}")

    required = [PROFILES_OUTPUT_FILE, DATASOURCE_OUTPUT_FILE, MEMORY_CARDS_OUTPUT_FILE]
    missing = [path for path in required if not Path(path).exists()]
    if missing:
        print("Missing required output files:")
        for path in missing:
            print(f"- {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
