"""
Verify the DDL specification against a live Neo4j instance.

Run inside the API container, which already has the neo4j driver and the
NEO4J_* environment variables from docker-compose:

    docker compose run --rm api python scripts/verify_neo4j.py

Proves four things the schema claims:

1. every statement in the DDL spec applies to our neo4j:5-community image;
2. applying the spec twice is a no-op (every statement is IF NOT EXISTS);
3. the seed fixture loads, and loading it a SECOND time does not duplicate
   anything - the deterministic-UUIDv5 + MERGE idempotency guarantee;
4. the Evidence-First invariants hold in the database, not just in Python.

Loading uses UNWIND batching over ``flatten_node`` output, which is the same
path the ingestion loader will take.
"""

from __future__ import annotations

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
                "props": edge.properties,
            }
        )
    for (src_label, rel, dst_label), rows in by_rel.items():
        session.run(
            f"UNWIND $rows AS row "
            f"MATCH (a:{src_label} {{id: row.src}}) "
            f"MATCH (b:{dst_label} {{id: row.dst}}) "
            f"MERGE (a)-[r:{rel}]->(b) "
            f"SET r += row.props",
            rows=rows,
        )


INVARIANTS = [
    (
        "no skill claim without supporting evidence",
        "MATCH (a:SkillAssertion) WHERE a.status <> 'no_evidence' "
        "AND NOT (a)-[:SUPPORTED_BY_EVIDENCE]->(:Evidence) RETURN count(a) AS c",
    ),
    (
        "no evidence without a traceable source",
        "MATCH (e:Evidence) WHERE NOT (e)-[:DERIVED_FROM]->() RETURN count(e) AS c",
    ),
    (
        "no evidence detached from a learner",
        "MATCH (e:Evidence) WHERE NOT (e)-[:EVIDENCE_FOR_LEARNER]->(:Learner) "
        "RETURN count(e) AS c",
    ),
    (
        "no observation without evidence",
        "MATCH (o:Observation) WHERE NOT (o)-[:SUPPORTED_BY_EVIDENCE]->(:Evidence) "
        "RETURN count(o) AS c",
    ),
    (
        "provenance coverage is 100%",
        "MATCH (e:Evidence) WHERE e.source_system IS NULL OR e.source_id IS NULL "
        "OR e.source_observed_at IS NULL RETURN count(e) AS c",
    ),
]


def main() -> int:
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
            session.run("MATCH (n) DETACH DELETE n")
            n0, r0 = counts(session)
            check("database emptied", n0 == 0 and r0 == 0, f"{n0} nodes, {r0} rels")

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

            print("\n4. Evidence-First invariants (each must return zero)")
            for name, query in INVARIANTS:
                got = session.run(query).single()["c"]
                check(name, got == 0, f"{got} violations")

            print("\n5. Uniqueness constraint actually bites")
            session.run("MATCH (n:Learner {id:'dup-test'}) DETACH DELETE n")
            session.run("CREATE (:Learner {id:'dup-test'})")
            try:
                session.run("CREATE (:Learner {id:'dup-test'})")
                check("duplicate Learner.id rejected", False, "duplicate accepted")
            except Exception:
                check("duplicate Learner.id rejected", True, "constraint enforced")
            session.run("MATCH (n:Learner {id:'dup-test'}) DETACH DELETE n")

            print("\n6. The demo traversal")
            rows = session.run(
                "MATCH (l:Learner)-[:HAS_SKILL_ASSERTION]->(a:SkillAssertion)"
                "-[:ABOUT_SKILL]->(s:Skill) "
                "MATCH (a)-[:SUPPORTED_BY_EVIDENCE]->(e:Evidence) "
                "RETURN s.canonical_name AS skill, a.tier AS tier, "
                "a.status AS strength, count(e) AS evidence, "
                "count(DISTINCT e.source_system) AS sources "
                "ORDER BY evidence DESC LIMIT 6"
            ).data()
            for row in rows:
                print(
                    f"    {row['skill']:24} {row['tier']:13} {row['strength']:9} "
                    f"{row['evidence']:3} evidence from {row['sources']} source(s)"
                )
            check("evidence traversal returns results", bool(rows), f"{len(rows)} rows")

            gaps = session.run(
                "MATCH (a:SkillAssertion)-[:ABOUT_SKILL]->(s:Skill) "
                "WHERE a.status = 'no_evidence' "
                "RETURN s.canonical_name AS skill, a.tier AS tier"
            ).data()
            print("\n   evidence gaps (what Epic 3 turns into a scenario):")
            for gap in gaps:
                print(f"    {gap['skill']} ({gap['tier']}) - no evidence found")
            check("evidence gap is queryable", bool(gaps), f"{len(gaps)} gap(s)")
    finally:
        driver.close()

    print("\n" + "=" * 74)
    print(f"{PASSED} passed, {FAILED} failed")
    print("=" * 74)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
