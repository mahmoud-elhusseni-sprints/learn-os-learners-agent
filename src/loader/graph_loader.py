"""
Graph loader entry point: connection management, schema initialization and
idempotent batch ingestion, in one place.

Why this module is a facade
---------------------------
The team's ``docs/architecture.md`` puts Neo4j code under
``src/app/graph/`` and ingestion under ``src/app/ingestion/``, and the rest
of the codebase imports from there. This module is the entry point the task
brief names (``src/loader/graph_loader.py``) and re-exports that same
implementation rather than copying it - one implementation, one set of
tests, no second copy to drift out of sync.

Use whichever import path suits you; they are the same objects.

Typical use
-----------

    from src.loader.graph_loader import (
        get_driver, verify_connection, initialize_schema, load_graph,
    )

    driver = get_driver()
    verify_connection(driver)     # fail fast on a bad URI/password
    initialize_schema(driver)     # idempotent - safe to re-run
    load_graph(driver, graph)     # idempotent - safe to re-run

Command line
------------

    python3 -m src.loader.graph_loader --seed tests/fixtures/sample_learner_seed.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from src.app.core.config import settings
from src.app.graph.connections import (
    GraphConnectionError,
    close_driver,
    get_driver,
    verify_connection,
)
from src.app.graph.constraints import ALL_STATEMENTS, initialize_schema
from src.app.graph.schema import LearnerGraph
from src.app.ingestion.build_graph import BuildResult, build_graph_from_files
from src.app.ingestion.loader import load_graph, load_graph_atomic

__all__ = [
    "get_driver",
    "verify_connection",
    "close_driver",
    "GraphConnectionError",
    "initialize_schema",
    "ALL_STATEMENTS",
    "load_graph",
    "load_graph_atomic",
    "load_seed_file",
    "load_pipeline_output",
]

logger = logging.getLogger(__name__)


def load_seed_file(path: Path, *, batch_size: int | None = None) -> LearnerGraph:
    """Validate a serialized ``LearnerGraph`` and load it into Neo4j.

    Validation happens before a single write: if the file is malformed, or
    an edge points at a node that isn't in it, nothing reaches the database.
    """
    graph = LearnerGraph.model_validate(json.loads(path.read_text(encoding="utf-8")))

    driver = get_driver()
    verify_connection(driver)
    initialize_schema(driver)
    load_graph(driver, graph, batch_size=batch_size)
    return graph


def load_pipeline_output(
    profiles_file: Path,
    datasource_file: Path,
    memory_cards_file: Path,
    *,
    extra_memory_cards_file: Path | None = None,
    batch_size: int | None = None,
) -> BuildResult:
    """Load the preprocessing pipeline's output into Neo4j.

    This is the seam between extraction and the graph: it converts records
    into graph models, validates the whole batch, then loads it. Records
    that could not be converted are reported in the returned
    ``BuildResult.skipped`` rather than silently dropped.

    ``extra_memory_cards_file`` is optional: Elgazzar's meeting/chat memory
    card generator (``src/app/ingestion/generate_memory_cards.py``) isn't
    part of ``pipeline.py`` yet, so its output (run with ``--format json``
    or ``jsonl``) is merged in here rather than assumed to already be in
    ``memory_cards_file``.
    """
    result = build_graph_from_files(
        profiles_file,
        datasource_file,
        memory_cards_file,
        extra_memory_cards_file=extra_memory_cards_file,
    )

    driver = get_driver()
    verify_connection(driver)
    initialize_schema(driver)
    load_graph(driver, result.graph, batch_size=batch_size)
    return result


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    # The driver logs an INFO notification for every `IF NOT EXISTS` statement
    # that was already satisfied - expected on a re-run, and it drowns out
    # everything else. Keep its warnings, drop the notifications.
    logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

    ap = argparse.ArgumentParser(description=__doc__)
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--seed",
        type=Path,
        help="Path to a serialized LearnerGraph JSON file to ingest.",
    )
    source.add_argument(
        "--pipeline-dir",
        type=Path,
        help=(
            "Directory holding the preprocessing pipeline's output "
            "(extracted_learner_profiles.json, graph_datasource_nodes.json, "
            "graph_memory_cards.json)."
        ),
    )
    ap.add_argument(
        "--extra-memory-cards",
        type=Path,
        default=None,
        help=(
            "Optional: output from Elgazzar's standalone "
            "generate_memory_cards.py (--format json or jsonl), merged in "
            "alongside --pipeline-dir's own memory cards. Not needed with "
            "--seed."
        ),
    )
    ap.add_argument(
        "--batch-size",
        type=int,
        default=settings.graph_loader_batch_size,
        help=f"Rows per statement (default: {settings.graph_loader_batch_size}).",
    )
    args = ap.parse_args(argv)

    try:
        if args.pipeline_dir:
            if not args.pipeline_dir.is_dir():
                print(f"no such directory: {args.pipeline_dir}", file=sys.stderr)
                return 2
            result = load_pipeline_output(
                args.pipeline_dir / "extracted_learner_profiles.json",
                args.pipeline_dir / "graph_datasource_nodes.json",
                args.pipeline_dir / "graph_memory_cards.json",
                extra_memory_cards_file=args.extra_memory_cards,
                batch_size=args.batch_size,
            )
            print(f"loaded {result.summary()}")
            for entry in result.skipped:
                print(f"  skipped: {entry}")
            for entry in result.duplicates:
                print(f"  duplicate: {entry}")
            close_driver()
            return 0

        if not args.seed.exists():
            print(f"no such file: {args.seed}", file=sys.stderr)
            return 2
        graph = load_seed_file(args.seed, batch_size=args.batch_size)
    except GraphConnectionError as exc:
        print(f"{exc}", file=sys.stderr)
        return 2
    finally:
        close_driver()

    counts = ", ".join(f"{k}={v}" for k, v in graph.counts().items())
    print(f"loaded {len(graph.nodes)} nodes ({counts}), {len(graph.edges)} edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
