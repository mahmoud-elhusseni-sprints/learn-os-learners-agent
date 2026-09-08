"""
Generate ``schema_constraints.cql`` from the (v2, minimal) Pydantic ontology.

Rewritten alongside the schema redesign. With only 3 node types the DDL
shrinks from 115 statements to a handful, but the generation principle is
unchanged: the DDL is derived from the models, never hand-written, so the
database rules cannot drift from the Python contract. A node label with no
DDL entry is still a hard error.

Edition note
------------
Neo4j **Community Edition supports uniqueness constraints and indexes
only**. ``docker-compose.yml`` pins ``neo4j:5-community``, so this file
contains only Community-safe statements.

Run:  python3 scripts/generate_constraints.py [--write-module]
"""

from __future__ import annotations

from pathlib import Path

import src.app.graph.schema as M

ROOT = Path(__file__).resolve().parent.parent
OUT_PY = ROOT / "src" / "app" / "graph" / "constraints.py"
OUT_CQL = ROOT / "docs" / "data" / "schema_constraints.cql"
#: Same DDL, at the path the task brief names as a deliverable. One
#: generator, two destinations - so the two files cannot drift apart.
OUT_SCHEMA_INIT = ROOT / "db" / "schema_init.cypher"

#: business_key: the property that uniquely identifies the node in the real
#: world - its own natural key from the source system.
#: indexes:      properties worth a range index for common lookups.
#: fulltext:     text properties worth full-text search.
DDL_SPEC: dict[str, dict[str, list[str]]] = {
    "LearnerProfile": {
        "business_key": ["learner_id"],
        "indexes": ["name", "role", "group_name", "round_name"],
        "fulltext": [],
    },
    "DataSource": {
        "business_key": ["datasource_id"],
        "indexes": ["datasource_name", "timestamp"],
        "fulltext": [],
    },
    "MemoryCard": {
        "business_key": ["card_id"],
        "indexes": ["metric_key", "created_at"],
        "fulltext": ["content", "rationale"],
    },
}


def _check_coverage() -> None:
    missing = sorted(set(M.NODE_CLASSES) - set(DDL_SPEC))
    extra = sorted(set(DDL_SPEC) - set(M.NODE_CLASSES))
    if missing or extra:
        raise SystemExit(
            f"DDL_SPEC is out of sync with the ontology.\n"
            f"  labels with no DDL entry: {missing}\n"
            f"  DDL entries with no label: {extra}"
        )


def _cname(label: str, suffix: str) -> str:
    return f"c_{label.lower()}_{suffix}"


def _iname(label: str, prop: str) -> str:
    return f"i_{label.lower()}_{prop}"


def _banner(text: str) -> list[str]:
    bar = "// " + "=" * 74
    return [bar, f"// {text}", bar, ""]


def build() -> str:
    """Render the human-readable .cql file (comments + Cypher)."""
    _check_coverage()
    labels = sorted(M.NODE_CLASSES)
    L: list[str] = []

    L += _banner("Professional Learner Graph - schema constraints and indexes")
    L += [
        f"// ontology version : {M.ONTOLOGY_VERSION}",
        f"// schema version   : {M.SCHEMA_VERSION}",
        f"// node labels      : {len(labels)}  ({', '.join(labels)})",
        f"// relationship types: {len(list(M.EdgeType))}",
        "//",
        "// GENERATED FILE - produced by scripts/generate_constraints.py from",
        "// src/app/graph/schema.py. Do not hand-edit; change the models and",
        "// regenerate.",
        "//",
        "// Neo4j Community Edition (docker-compose.yml pins neo4j:5-community):",
        "// uniqueness constraints and indexes only. No property-existence",
        "// constraints are emitted - those are Enterprise-only. The Pydantic",
        "// models are the enforcement layer for required properties.",
        "//",
        "// Every statement uses IF NOT EXISTS, so this file is idempotent.",
        "",
        "",
    ]

    L += _banner("1. Primary key uniqueness")
    for label in labels:
        L.append(
            f"CREATE CONSTRAINT {_cname(label, 'id_unique')} IF NOT EXISTS\n"
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE;"
        )
    L.append("")

    L += _banner("2. Business key uniqueness")
    L += [
        "// Guards against the same real-world record being ingested twice",
        "// under two different generated ids.",
        "",
    ]
    for label in labels:
        keys = DDL_SPEC[label]["business_key"]
        if not keys:
            continue
        req = ", ".join(f"n.{k}" for k in keys)
        req = f"({req})" if len(keys) > 1 else req
        L.append(
            f"CREATE CONSTRAINT {_cname(label, 'bkey_unique')} IF NOT EXISTS\n"
            f"FOR (n:{label}) REQUIRE {req} IS UNIQUE;"
        )
    L.append("")

    L += _banner("3. Range indexes")
    for label in labels:
        for prop in DDL_SPEC[label]["indexes"]:
            L.append(
                f"CREATE INDEX {_iname(label, prop)} IF NOT EXISTS\n"
                f"FOR (n:{label}) ON (n.{prop});"
            )
    L.append("")

    L += _banner("4. Full-text indexes")
    for label in labels:
        props = DDL_SPEC[label]["fulltext"]
        if not props:
            continue
        plist = ", ".join(f"n.{p}" for p in props)
        L.append(
            f"CREATE FULLTEXT INDEX ft_{label.lower()} IF NOT EXISTS\n"
            f"FOR (n:{label}) ON EACH [{plist}];"
        )
    L.append("")

    L += _banner("5. Verification queries (run manually after loading the seed)")
    L += [
        "// SHOW CONSTRAINTS;",
        "// SHOW INDEXES;",
        "",
        "// A learner's full trail: their source records and the memory",
        "// cards extracted from them.",
        "// MATCH (l:LearnerProfile "
        "{learner_id: '127c834c-f7ce-4cc7-9a73-c8f93c8648aa'})",
        "//       -[:PRODUCED]->(d:DataSource)",
        "// OPTIONAL MATCH (d)-[:EXTRACTED_INTO]->(m:MemoryCard)",
        "// RETURN d.datasource_name, d.timestamp, m.metric_key, m.content",
        "// ORDER BY d.timestamp;",
        "",
        "// Idempotency check: record counts, re-run the seed load, re-run this.",
        "// MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label;",
        "// MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS rels ORDER BY rel;",
    ]

    return "\n".join(L).rstrip() + "\n"


def build_python() -> str:
    """Emit src/app/graph/constraints.py as plain Cypher-string lists,
    matching the style Arwa's integration workstream already uses."""
    _check_coverage()
    labels = sorted(M.NODE_CLASSES)

    constraints: list[str] = []
    for label in labels:
        constraints.append(
            f"CREATE CONSTRAINT {_cname(label, 'id_unique')} IF NOT EXISTS\n"
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
        )
    for label in labels:
        keys = DDL_SPEC[label]["business_key"]
        if not keys:
            continue
        req = ", ".join(f"n.{k}" for k in keys)
        req = f"({req})" if len(keys) > 1 else req
        constraints.append(
            f"CREATE CONSTRAINT {_cname(label, 'bkey_unique')} IF NOT EXISTS\n"
            f"FOR (n:{label}) REQUIRE {req} IS UNIQUE"
        )

    indexes: list[str] = []
    for label in labels:
        for prop in DDL_SPEC[label]["indexes"]:
            indexes.append(
                f"CREATE INDEX {_iname(label, prop)} IF NOT EXISTS\n"
                f"FOR (n:{label}) ON (n.{prop})"
            )

    fulltext: list[str] = []
    for label in labels:
        props = DDL_SPEC[label]["fulltext"]
        if not props:
            continue
        plist = ", ".join(f"n.{p}" for p in props)
        fulltext.append(
            f"CREATE FULLTEXT INDEX ft_{label.lower()} IF NOT EXISTS\n"
            f"FOR (n:{label}) ON EACH [{plist}]"
        )

    def render_list(name: str, stmts: list[str], doc: str) -> str:
        lines = [f"#: {doc}", f"{name}: list[str] = ["]
        for stmt in stmts:
            body = "\n".join("    " + ln.strip() for ln in stmt.splitlines())
            lines.append('    """')
            lines.append(body)
            lines.append('    """,')
        lines.append("]")
        return "\n".join(lines)

    header = f'''"""
Neo4j constraints and indexes for the Professional Learner Graph (v2, minimal).

GENERATED FILE - produced by ``scripts/generate_constraints.py`` from
``src/app/graph/schema.py``. Do not hand-edit; change the models and
regenerate so the database rules cannot drift from the Python contract.

3 node labels ({", ".join(labels)}), Community Edition safe.
Every statement uses ``IF NOT EXISTS``, so applying these repeatedly is safe.

ontology version : {M.ONTOLOGY_VERSION}
"""

from __future__ import annotations

from neo4j import Driver
'''
    parts = [
        header,
        render_list("CONSTRAINTS", constraints, "Uniqueness constraints."),
        "",
        render_list("INDEXES", indexes, "Range indexes on common lookups."),
        "",
        render_list("FULLTEXT_INDEXES", fulltext, "Full-text search indexes."),
        "",
        "#: Every statement, in order. All of it is safe on Neo4j 5 Community.",
        "ALL_STATEMENTS: list[str] = CONSTRAINTS + INDEXES + FULLTEXT_INDEXES",
        "",
        "",
        "def initialize_schema(driver: Driver) -> None:",
        '    """Apply every constraint and index. Safe to call more than once -',
        "    every statement is ``IF NOT EXISTS``, so a second call is a no-op",
        '    rather than an error."""',
        "    with driver.session() as session:",
        "        for statement in ALL_STATEMENTS:",
        "            session.run(statement)",
        "",
    ]
    return "\n".join(parts)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--write-module",
        action="store_true",
        help=(
            "Also overwrite src/app/graph/constraints.py. That file is owned by "
            "the Neo4j/integration workstream - only pass this if you own it."
        ),
    )
    args = ap.parse_args()

    ddl = build()

    OUT_CQL.parent.mkdir(parents=True, exist_ok=True)
    OUT_CQL.write_text(ddl, encoding="utf-8")
    print(f"wrote {OUT_CQL.relative_to(ROOT)}")

    OUT_SCHEMA_INIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_SCHEMA_INIT.write_text(ddl, encoding="utf-8")
    print(f"wrote {OUT_SCHEMA_INIT.relative_to(ROOT)}")

    if args.write_module:
        OUT_PY.parent.mkdir(parents=True, exist_ok=True)
        OUT_PY.write_text(build_python(), encoding="utf-8")
        print(f"wrote {OUT_PY.relative_to(ROOT)}")
    else:
        print(
            "skipped src/app/graph/constraints.py (owned by the integration "
            "workstream) - pass --write-module to generate it"
        )
