from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load generated learner data into Neo4j."
    )
    parser.add_argument(
        "--pipeline-dir",
        type=Path,
        default=None,
        help="Directory containing the three generated JSON files.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Optional number of rows per Neo4j write batch.",
    )
    args = parser.parse_args()

    from src.app.core.config import (  # noqa: PLC0415
        DATASOURCE_OUTPUT_FILE,
        MEMORY_CARDS_OUTPUT_FILE,
        PROFILES_OUTPUT_FILE,
    )
    from src.app.graph.connections import (  # noqa: PLC0415
        GraphConnectionError,
        close_driver,
    )
    from src.loader.graph_loader import load_pipeline_output  # noqa: PLC0415

    pipeline_dir = args.pipeline_dir or Path(MEMORY_CARDS_OUTPUT_FILE).parent
    paths = {
        "profiles": pipeline_dir / Path(PROFILES_OUTPUT_FILE).name,
        "data sources": pipeline_dir / Path(DATASOURCE_OUTPUT_FILE).name,
        "memory cards": pipeline_dir / Path(MEMORY_CARDS_OUTPUT_FILE).name,
    }
    missing = [f"{name}: {path}" for name, path in paths.items() if not path.exists()]
    if missing:
        print("Run test_preprocessing.py first. Missing:")
        for item in missing:
            print(f"- {item}")
        return 1

    try:
        result = load_pipeline_output(
            paths["profiles"],
            paths["data sources"],
            paths["memory cards"],
            batch_size=args.batch_size,
        )
        print("Data loading test completed.")
        print(f"- {result.summary()}")
        for entry in result.skipped:
            print(f"- skipped: {entry}")
        for entry in result.duplicates:
            print(f"- duplicate: {entry}")
        return 0
    except GraphConnectionError as exc:
        print(f"Neo4j is unavailable: {exc}")
        return 2
    finally:
        close_driver()


if __name__ == "__main__":
    raise SystemExit(main())
