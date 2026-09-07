"""
Verify the DDL specification against a live Neo4j instance
(v2, minimal schema: LearnerProfile / DataSource / MemoryCard).

Run inside the API container, which already has the neo4j driver and the
NEO4J_* environment variables from docker-compose:

    docker compose run --rm api python scripts/verify_neo4j.py --reset

By default this script REFUSES to run against a non-empty database and
does not touch existing data. Pass ``--reset`` only when you mean to wipe
the target database first (a dedicated test/dev Neo4j instance) - it runs
an unconditional ``MATCH (n) DETACH DELETE n`` before verifying, so never
pass it against a shared or production database.

Proves three things the schema claims:

1. every statement in the DDL spec applies to our neo4j:5-community image;
2. applying the spec twice is a no-op (every statement is IF NOT EXISTS);
3. the seed fixture loads, and loading it a SECOND time does not duplicate
   anything - the deterministic-UUIDv5 + MERGE idempotency guarantee.

There is no "Evidence-First" invariant check here, unlike v1: that
invariant protected a graph of Evidence/SkillAssertion nodes which do not
exist in this design. See src/app/graph/schema.py's module docstring for
why this is a deliberate, flagged change rather than an oversight.

Loading uses UNWIND batching over ``flatten_node`` output, which is the same
path the ingestion loader will take.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    # Make the script runnable as `python scripts/verify_neo4j.py` from the
    # container, where only /app/scripts lands on sys.path by default.
    sys.path.insert(0, str(ROOT))

from neo4j import GraphDatabase  # noqa: E402

import src.app.graph.schema as M  # noqa: E402
from scripts import generate_constraints as GS  # noqa: E402
from src.app.graph.serialization import flatten_node  # noqa: E402

SEED = ROOT / "tests" / "fixtures" / "sample_learner_seed.json"

PASSED = 0
FAILED = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        mark = "PASS"
    else:
        FAILED += 1
        mark = "FAIL"
    print(f"  [{mark}] {name}" + (f"  -- {detail}" if detail else ""))


def ddl_statements() -> list[str]:
    """The Community-safe statements from the generated spec."""
    ns: dict[str, Any] = {}
    exec(GS.build_python(), ns)
    return [" ".join(s.split()) for s in ns["ALL_STATEMENTS"]]


def counts(session: Any) -> tuple[int, int]:
    nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
    rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
    return nodes, rels


def load_graph(session: Any, graph: M.LearnerGraph) -> None:
    """Load via UNWIND + MERGE - the same path the ingestion loader uses."""
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in graph.nodes:
        by_label[node.label].append(flatten_node(node))
    for label, rows in by_label.items():
        session.run(
            f"UNWIND $rows AS row MERGE (n:{label} {{id: row.id}}) SET n += row",
            rows=rows,
        )

    by_rel: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in graph.edges:
        key = (edge.source_label, edge.type.value, edge.target_label)
        by_rel[key].append(
            {
                "src": str(edge.source_id),
                "dst": str(edge.target_id),
            }
        )
    for (src_label, rel, dst_label), rows in by_rel.items():
        session.run(
            f"UNWIND $rows AS row "
            f"MATCH (a:{src_label} {{id: row.src}}) "
            f"MATCH (b:{dst_label} {{id: row.dst}}) "
            f"MERGE (a)-[r:{rel}]->(b)",
            rows=rows,
        )


INVARIANTS = [
    (
        "every DataSource's persisted payload_json matches its own "
        "datasource_name's expected shape",
        # Neo4j Community has no JSON-parsing function without APOC, so this
        # checks the persisted payload_json for the field names each shape
        # must carry (ReviewPayload/AssessmentPayload) rather than parsing
        # it structurally - weaker than the Pydantic validation that ran
        # before insert, but it verifies the shape actually landed in the
        # database instead of only checking payload_json is non-null (which
        # is true for every DataSource, including empty-payload stubs, and
        # would never catch a swapped or truncated payload).
        "MATCH (d:DataSource) WHERE "
        "(d.datasource_name = 'review' AND NOT ("
        "d.payload_json CONTAINS '\"verdict\"' AND "
        "d.payload_json CONTAINS '\"submission_text\"')) OR "
        "(d.datasource_name = 'assesments' AND NOT ("
        "d.payload_json CONTAINS '\"score\"' AND "
        "d.payload_json CONTAINS '\"max_score\"')) OR "
        "(d.datasource_name IN ['chat', 'meetings'] AND "
        "d.payload_json <> '{}') "
        "RETURN count(d) AS c",
    ),
    (
        "no MemoryCard detached from a learner (HAS_MEMORY_CARD)",
        "MATCH (m:MemoryCard) WHERE NOT (:LearnerProfile)-[:HAS_MEMORY_CARD]->(m) "
        "RETURN count(m) AS c",
    ),
    (
        "no DataSource detached from a learner (PRODUCED)",
        "MATCH (d:DataSource) WHERE NOT (:LearnerProfile)-[:PRODUCED]->(d) "
        "RETURN count(d) AS c",
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Wipe the target database (MATCH (n) DETACH DELETE n) before "
            "verifying. Only pass this against a dedicated test/dev "
            "instance - never a shared or production database."
        ),
    )
    args = ap.parse_args()

    uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        print("NEO4J_PASSWORD is not set - is .env present and loaded?")
        return 2

    print("=" * 74)
    print("Neo4j verification - Professional Learner Graph DDL specification")
    print(f"target: {uri}")
    print("=" * 74)

    graph = M.LearnerGraph.model_validate(json.loads(SEED.read_text(encoding="utf-8")))
    statements = ddl_statements()

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        with driver.session() as session:
            print("\n0. Clean slate")
            n_existing, r_existing = counts(session)
            if args.reset:
                session.run("MATCH (n) DETACH DELETE n")
                n0, r0 = counts(session)
                check("database emptied", n0 == 0 and r0 == 0, f"{n0} nodes, {r0} rels")
            elif n_existing or r_existing:
                print(
                    f"  [ABORT] target database is not empty "
                    f"({n_existing} nodes, {r_existing} rels) and --reset "
                    f"was not passed. Refusing to write into a database "
                    f"that might hold real or someone else's data. Re-run "
                    f"with --reset only against a dedicated test/dev "
                    f"instance."
                )
                return 2
            else:
                check("database already empty (no reset needed)", True)

            print("\n1. DDL applies to neo4j:5-community")
            failures: list[str] = []
            for stmt in statements:
                try:
                    session.run(stmt)
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{stmt[:60]}... -> {exc}")
            check(
                f"all {len(statements)} statements applied",
                not failures,
                failures[0] if failures else "no errors",
            )
            c1 = session.run(
                "SHOW CONSTRAINTS YIELD name RETURN count(*) AS c"
            ).single()["c"]
            i1 = session.run("SHOW INDEXES YIELD name RETURN count(*) AS c").single()[
                "c"
            ]
            check("constraints created", c1 > 0, f"{c1} constraints, {i1} indexes")

            print("\n2. Re-applying the DDL is a no-op")
            for stmt in statements:
                session.run(stmt)
            c2 = session.run(
                "SHOW CONSTRAINTS YIELD name RETURN count(*) AS c"
            ).single()["c"]
            check("constraint count unchanged", c1 == c2, f"{c1} -> {c2}")

            print("\n3. Seed loads, and re-loading does not duplicate")
            load_graph(session, graph)
            n1, r1 = counts(session)
            check(
                "first load matches the fixture",
                n1 == len(graph.nodes) and r1 == len(graph.edges),
                f"{n1} nodes / {r1} rels (fixture: "
                f"{len(graph.nodes)} / {len(graph.edges)})",
            )
            load_graph(session, graph)
            n2, r2 = counts(session)
            check(
                "IDEMPOTENT - second load changed nothing",
                (n1, r1) == (n2, r2),
                f"{n1}/{r1} -> {n2}/{r2}",
            )

            print("\n4. Invariants (each must return zero)")
            for name, query in INVARIANTS:
                got = session.run(query).single()["c"]
                check(name, got == 0, f"{got} violations")

            print("\n5. Uniqueness constraint actually bites")
            session.run("MATCH (n:LearnerProfile {id:'dup-test'}) DETACH DELETE n")
            session.run("CREATE (:LearnerProfile {id:'dup-test'})")
            try:
                session.run("CREATE (:LearnerProfile {id:'dup-test'})")
                check(
                    "duplicate LearnerProfile.id rejected", False, "duplicate accepted"
                )
            except Exception:
                check(
                    "duplicate LearnerProfile.id rejected", True, "constraint enforced"
                )
            session.run("MATCH (n:LearnerProfile {id:'dup-test'}) DETACH DELETE n")

            print("\n6. The demo traversal")
            rows = session.run(
                "MATCH (l:LearnerProfile)-[:PRODUCED]->(d:DataSource) "
                "OPTIONAL MATCH (d)-[:EXTRACTED_INTO]->(m:MemoryCard) "
                "RETURN l.name AS learner, d.datasource_name AS datasource, "
                "count(DISTINCT d) AS records, count(m) AS memory_cards "
                "ORDER BY records DESC LIMIT 6"
            ).data()
            for row in rows:
                print(
                    f"    {row['learner']:16} {row['datasource']:12} "
                    f"{row['records']:3} record(s) -> "
                    f"{row['memory_cards']:3} memory card(s)"
                )
            check(
                "learner -> source -> memory card traversal returns results",
                bool(rows),
                f"{len(rows)} rows",
            )
    finally:
        driver.close()

    print("\n" + "=" * 74)
    print(f"{PASSED} passed, {FAILED} failed")
    print("=" * 74)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
