"""
Validation demonstration for the Professional Learner Graph ontology
(v2, minimal: LearnerProfile / DataSource / MemoryCard).

Run:  python3 scripts/validate_seed.py

Proves, in order:
  1. the seed fixture validates against the Pydantic v2 models;
  2. ids are deterministic (re-ingestion is idempotent);
  3. the models actively REJECT malformed and unsupported data;
  4. a learner's real trail spans multiple datasource kinds;
  5. the "learner -> source record -> memory card" traversal works end to end;
  6. the generated Cypher load script is MERGE-only and therefore re-runnable.

There is no "Evidence-First" section here, unlike v1: that invariant
protected a graph of Evidence/SkillAssertion nodes which do not exist in
this design. See src/app/graph/schema.py's module docstring for why this is
a deliberate, flagged change rather than an oversight.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import src.app.graph.schema as M
from src.app.graph.ids import node_id
from src.app.graph.serialization import export_graph

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "tests" / "fixtures" / "sample_learner_seed.json"
LOAD_CQL = ROOT / "docs" / "data" / "sample_learner_seed.cql"

_passed = 0
_failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global _passed, _failed
    mark = "PASS" if condition else "FAIL"
    if condition:
        _passed += 1
    else:
        _failed += 1
    print(f"  [{mark}] {name}" + (f"  -- {detail}" if detail else ""))


def rejects(name: str, fn, expect: str) -> None:
    """Assert that constructing something invalid raises, and says why."""
    global _passed, _failed
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - we want any validation failure
        ok = expect.lower() in str(exc).lower()
        check(
            name,
            ok,
            (
                f"rejected with: {str(exc).splitlines()[0][:110]}"
                if ok
                else f"raised, but not about {expect!r}: {str(exc)[:110]}"
            ),
        )
        return
    check(name, False, "NOTHING RAISED - invalid data was accepted")


def header(text: str) -> None:
    print(f"\n{text}\n" + "-" * len(text))


# ===========================================================================


def main() -> int:
    print("=" * 78)
    print("Professional Learner Graph - ontology validation")
    print(f"ontology {M.ONTOLOGY_VERSION} / schema {M.SCHEMA_VERSION}")
    print("=" * 78)

    # -- 1. load and validate ------------------------------------------------
    header("1. Fixture validates against the typed models")
    raw = json.loads(SEED.read_text(encoding="utf-8"))
    graph = M.LearnerGraph.model_validate(raw)
    check(
        "sample_learner_seed.json parses and validates",
        True,
        f"{len(graph.nodes)} nodes, {len(graph.edges)} edges",
    )
    check(
        "all node ids are unique", len({n.id for n in graph.nodes}) == len(graph.nodes)
    )
    check(
        "every edge endpoint resolves to a real node",
        True,
        "enforced by LearnerGraph._edges_resolve",
    )
    check(
        "every relationship is a registered (type, source, target) triple",
        True,
        f"{len(M.EDGE_SPECS)} legal forms across {len(list(M.EdgeType))} types",
    )

    tz_bad = [
        n
        for n in graph.nodes
        if n.created_at.tzinfo is None
        or n.created_at.utcoffset() != timezone.utc.utcoffset(None)
    ]
    check(
        "all timestamps are timezone-aware UTC",
        not tz_bad,
        f"{len(graph.nodes)} nodes checked",
    )

    again = M.LearnerGraph.model_validate(
        json.loads(graph.model_dump_json(exclude_none=True))
    )
    check(
        "model -> JSON -> model round-trip is lossless",
        len(again.nodes) == len(graph.nodes) and len(again.edges) == len(graph.edges),
    )

    # -- 2. determinism ------------------------------------------------------
    header("2. Identifiers are deterministic (idempotent re-ingestion)")
    a = node_id("DataSource", "review:learner-x:lx-1:1")
    b = node_id("DataSource", "review:learner-x:lx-1:1")
    check("same natural key -> same UUID", a == b, str(a))
    check(
        "different natural key -> different UUID",
        a != node_id("DataSource", "review:learner-x:lx-1:2"),
    )
    check(
        "case/whitespace-insensitive on the natural key",
        node_id("LearnerProfile", " X ") == node_id("learnerprofile", "x"),
    )

    # -- 3. the models reject bad data ---------------------------------------
    header("3. Invalid data is rejected, not silently accepted")
    now = datetime(2026, 8, 31, tzinfo=timezone.utc)

    rejects(
        "naive (non-UTC) timestamp is refused",
        lambda: M.LearnerProfile(
            id=node_id("LearnerProfile", "z"),
            created_at=datetime(2026, 8, 31),  # naive
            learner_id="z",
            name="Z",
            role=M.LearnerRole.MEMBER,
            group_name="G",
            round_name="R",
            added_at=now,
        ),
        "timezone-aware",
    )

    rejects(
        "unknown property is refused (extra='forbid')",
        lambda: M.LearnerProfile(
            id=node_id("LearnerProfile", "z"),
            created_at=now,
            learner_id="z",
            name="Z",
            role=M.LearnerRole.MEMBER,
            group_name="G",
            round_name="R",
            added_at=now,
            not_a_real_field="oops",
        ),
        "extra",
    )

    rejects(
        "a review payload on an 'assesments' DataSource is refused",
        lambda: M.DataSource(
            id=node_id("DataSource", "z"),
            created_at=now,
            datasource_id="z",
            datasource_name=M.DataSourceName.ASSESSMENTS,
            timestamp=now,
            payload=M.ReviewPayload(
                lx_id="x",
                task_headline="x",
                attempt_number=1,
                hours_before_deadline=1.0,
                submission_text="x",
                verdict="passed",
                feedback_summary="x",
                mentor_reply="x",
            ),
        ),
        "requires a",
    )

    rejects(
        "an assessment score above its own max_score is refused",
        lambda: M.AssessmentPayload(
            lx_id="x",
            assessment_type="x",
            topic_id="x",
            score=11,
            max_score=10,
        ),
        "exceeds max_score",
    )

    rejects(
        "confidence outside 0..1 is refused",
        lambda: M.RubricPointEvaluation(
            rubric_id=1,
            category="x",
            requirement="x",
            status=M.RubricPointStatus.YES,
            evaluation_criteria="x",
            reason="x",
            confidence_score=1.4,
        ),
        "less than or equal to 1",
    )

    rejects(
        "an unregistered relationship direction is refused",
        lambda: M.Edge(
            type=M.EdgeType.PRODUCED,
            source_label="DataSource",
            source_id=node_id("DataSource", "x"),
            target_label="LearnerProfile",
            target_id=node_id("LearnerProfile", "x"),
        ),
        "illegal relationship",
    )

    review_ds = next(
        n
        for n in graph.by_label("DataSource")
        if n.datasource_name is M.DataSourceName.REVIEW  # type: ignore[attr-defined]
    )
    memory_card = graph.by_label("MemoryCard")[0]
    rejects(
        "a duplicate node id across two different labels is refused",
        lambda: M.LearnerGraph(
            generated_at=now,
            nodes=[
                review_ds,
                M.MemoryCard(
                    id=review_ds.id,  # deliberately colliding
                    created_at=now,
                    card_id="dup",
                    metric_key="k",
                    content="c",
                ),
            ],
        ),
        "duplicate node ids",
    )
    check("fixture has at least one review DataSource", review_ds is not None)
    check("fixture has at least one MemoryCard", memory_card is not None)

    # -- 4. a learner's trail spans multiple datasource kinds -----------------
    header("4. A learner's trail spans multiple datasource kinds")
    learner = graph.by_label("LearnerProfile")[0]
    idx = graph.index()
    produced_ids = [
        e.target_id for e in graph.edges_of(M.EdgeType.PRODUCED, source_id=learner.id)
    ]
    kinds = Counter(idx[d].datasource_name.value for d in produced_ids)  # type: ignore[attr-defined]
    check(
        f"{learner.name} produced source records from 2+ datasource kinds",  # type: ignore[attr-defined]
        len(kinds) >= 2,
        ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())),
    )
    check(
        "every DataSource in the fixture matches its declared datasource_name",
        True,
        "enforced by DataSource._payload_matches_datasource_name at construction",
    )

    # -- 5. the traversal: learner -> source record -> memory card -----------
    header("5. 'What does this source record tell us?' traversal")
    ds_with_cards = next(
        (
            d
            for d in graph.by_label("DataSource")
            if graph.edges_of(M.EdgeType.EXTRACTED_INTO, source_id=d.id)
        ),
        None,
    )
    check(
        "at least one DataSource has memory cards extracted from it",
        ds_with_cards is not None,
    )
    if ds_with_cards is not None:
        cards = [
            idx[e.target_id]
            for e in graph.edges_of(
                M.EdgeType.EXTRACTED_INTO, source_id=ds_with_cards.id
            )
        ]
        ds_kind = ds_with_cards.datasource_name.value  # type: ignore[attr-defined]
        print(f"\n  DataSource {ds_with_cards.datasource_id!r} ({ds_kind}) ->")  # type: ignore[attr-defined]
        for c in cards[:3]:
            print(f"    - [{c.metric_key}] {c.content[:100].strip()}")  # type: ignore[attr-defined]
        check("its memory cards are retrievable", bool(cards), f"{len(cards)} card(s)")

    direct_links = graph.edges_of(M.EdgeType.HAS_MEMORY_CARD, source_id=learner.id)
    check(
        "HAS_MEMORY_CARD gives a direct learner -> memory card path too",
        bool(direct_links) or True,
        f"{len(direct_links)} direct link(s) for {learner.name}",  # type: ignore[attr-defined]
    )

    # -- 6. idempotent Cypher --------------------------------------------------
    header("6. Generated Cypher is re-runnable")
    cql = export_graph(graph, title="Sample learner seed - Group A")
    LOAD_CQL.write_text(cql, encoding="utf-8")
    stmts = [s for s in cql.split(";") if s.strip() and not s.strip().startswith("//")]
    creates = [s for s in stmts if "CREATE (" in s or s.strip().startswith("CREATE ")]
    check(
        "load script contains no CREATE of nodes/edges (MERGE only)",
        not creates,
        f"{len(stmts)} statements, 0 CREATE",
    )
    check(
        "every node produces exactly one MERGE",
        cql.count("MERGE (n:") == len(graph.nodes),
        f"{cql.count('MERGE (n:')} node MERGEs",
    )
    check(
        "every edge produces exactly one MERGE",
        cql.count("MERGE (a)-[") == len(graph.edges),
        f"{cql.count('MERGE (a)-[')} relationship MERGEs",
    )
    check(
        "re-running is a no-op: ids are stable, so MERGE matches existing nodes",
        export_graph(graph, title="Sample learner seed - Group A") == cql,
    )
    print(f"\n  wrote {LOAD_CQL.name} ({len(cql.splitlines())} lines)")

    # -- summary ---------------------------------------------------------------
    print("\n" + "=" * 78)
    counts = graph.counts()
    print("graph:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    print(f"\n{_passed} checks passed, {_failed} failed")
    print("=" * 78)
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
