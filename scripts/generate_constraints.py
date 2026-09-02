"""
Generate ``schema_constraints.cql`` from the Pydantic ontology.

Generating rather than hand-writing the DDL means the database constraints
can never drift away from ``learner_graph_models.py``: required properties
are read straight off the model fields, and a node label with no DDL entry
is a hard error.

Edition note
------------
Neo4j **Community Edition supports uniqueness constraints and indexes only**.
Property *existence* constraints and *node key* constraints are Enterprise
features.  The generated file therefore splits into a Community-safe section
that always applies and an Enterprise section that is commented out by
default.  On Community, the Pydantic models are the enforcement layer for
required properties - which is why ``extra='forbid'`` and required fields
matter as much as they do.

Run:  python3 generate_schema.py
"""

from __future__ import annotations

from pathlib import Path

import src.app.graph.schema as M
from src.app.graph.serialization import required_neo4j_properties

ROOT = Path(__file__).resolve().parent.parent
OUT_PY = ROOT / "src" / "app" / "graph" / "constraints.py"
OUT_CQL = ROOT / "docs" / "data" / "schema_constraints.cql"

#: business_key: properties that uniquely identify the node in the real world.
#: indexes:      properties on hot filter/sort paths for Epics 2 and 3.
#: fulltext:     text properties that Sprint 3 hybrid retrieval searches.
DDL_SPEC: dict[str, dict[str, list[str]]] = {
    "Cohort": {"business_key": ["cohort_key"], "indexes": [], "fulltext": []},
    "Round": {"business_key": ["round_key"], "indexes": [], "fulltext": []},
    "Group": {"business_key": ["group_key"], "indexes": ["track"], "fulltext": []},
    "Learner": {
        "business_key": ["canonical_email"],
        "indexes": ["display_name", "source_system"],
        "fulltext": [],
    },
    "LearnerIdentity": {
        "business_key": ["source_system", "source_learner_id"],
        "indexes": ["resolution_status", "source_email"],
        "fulltext": [],
    },
    "Skill": {
        "business_key": ["slug"],
        "indexes": ["canonical_name", "category"],
        "fulltext": ["canonical_name", "description"],
    },
    "TaskDefinition": {
        "business_key": ["task_definition_key"],
        "indexes": ["task_archetype"],
        "fulltext": ["headline", "description"],
    },
    "Project": {"business_key": ["project_key"], "indexes": [], "fulltext": ["name"]},
    "LearningExperience": {
        "business_key": ["lx_key"],
        "indexes": ["status", "outcome", "activated_at", "deadline_at"],
        "fulltext": [],
    },
    "Attempt": {
        "business_key": ["source_system", "source_id"],
        "indexes": ["verdict", "evaluated_at"],
        "fulltext": [],
    },
    "Submission": {
        "business_key": ["source_system", "source_id"],
        "indexes": ["kind", "submitted_at", "is_resubmission"],
        "fulltext": ["text"],
    },
    "Artifact": {
        "business_key": ["source_system", "source_id"],
        "indexes": ["artifact_key", "artifact_type"],
        "fulltext": ["content_excerpt"],
    },
    "Rubric": {"business_key": ["rubric_key"], "indexes": [], "fulltext": []},
    "RubricCriterion": {
        "business_key": ["criterion_key"],
        "indexes": ["category"],
        "fulltext": ["requirement", "description"],
    },
    "Assessment": {
        "business_key": ["source_system", "source_id"],
        "indexes": [
            "assessment_kind",
            "verdict",
            "evaluated_at",
            "criteria_met",
            "criteria_total",
        ],
        "fulltext": ["summary", "mentor_reply"],
    },
    "Meeting": {
        "business_key": ["meeting_key"],
        "indexes": [
            "kind",
            "starts_at_utc",
            "extraction_status",
            "transcript_available",
        ],
        "fulltext": ["topic"],
    },
    "Interaction": {
        "business_key": ["source_system", "source_id"],
        "indexes": [
            "interaction_kind",
            "occurred_at",
            "struggle_area",
            "initiated_by",
            "carries_feedback",
        ],
        "fulltext": ["summary"],
    },
    # Evidence/derived nodes are keyed by their deterministic UUIDv5, which
    # already encodes (source_system, source_type, source_id, discriminators).
    # A second composite constraint would add no safety and would break on the
    # legitimately-null source_locator.
    "Evidence": {
        "business_key": [],
        "indexes": [
            "evidence_type",
            "strength",
            "observed_at",
            "access_scope",
            "source_system",
            "confidence",
        ],
        "fulltext": ["title", "content"],
    },
    "Observation": {
        "business_key": [],
        "indexes": ["category", "observed_at", "confidence"],
        "fulltext": ["context", "behavior", "outcome"],
    },
    "SkillAssertion": {
        "business_key": [],
        "indexes": [
            "tier",
            "status",
            "confidence",
            "latest_evidence_at",
            "evidence_count",
        ],
        "fulltext": ["rationale"],
    },
    "CareerGoal": {
        "business_key": [],
        "indexes": ["status", "target_role"],
        "fulltext": ["target_role"],
    },
    "Scenario": {
        "business_key": ["scenario_key"],
        "indexes": ["difficulty", "approved"],
        "fulltext": ["title", "description"],
    },
    "Recommendation": {
        "business_key": [],
        "indexes": ["gap_type", "status", "priority"],
        "fulltext": ["reason"],
    },
    "Employer": {"business_key": ["employer_key"], "indexes": ["name"], "fulltext": []},
    "AccessGrant": {
        "business_key": ["grant_key"],
        "indexes": ["granted_at", "expires_at"],
        "fulltext": [],
    },
}

#: Relationship properties worth indexing for Epic 2/3 filtering (Neo4j 5.x).
REL_INDEXES: list[tuple[str, str]] = [
    ("DEMONSTRATED_SKILL", "status"),
    ("DEMONSTRATED_SKILL", "confidence"),
    ("ASSESSED_ON_SKILL", "status"),
    ("SCORED_CRITERION", "status"),
    ("COMPLETED_TASK", "outcome"),
    # Evidence provenance lives on the DERIVED_FROM edge; employers filter on it.
    ("DERIVED_FROM", "extraction_confidence"),
    ("CONTAINS_ARTIFACT", "cited_by_grader"),
    ("EVALUATED_BY", "verdict"),
    ("SUBMITTED", "attempt_number"),
]


def _check_coverage() -> None:
    missing = sorted(set(M.NODE_CLASSES) - set(DDL_SPEC))
    extra = sorted(set(DDL_SPEC) - set(M.NODE_CLASSES))
    if missing or extra:
        raise SystemExit(
            f"DDL_SPEC is out of sync with the ontology.\n"
            f"  labels with no DDL entry: {missing}\n"
            f"  DDL entries with no label: {extra}"
        )


def _banner(text: str) -> list[str]:
    bar = "// " + "=" * 74
    return [bar, f"// {text}", bar, ""]


def build() -> str:
    _check_coverage()
    labels = sorted(M.NODE_CLASSES)
    L: list[str] = []

    L += _banner("Professional Learner Graph - schema constraints and indexes")
    L += [
        f"// ontology version : {M.ONTOLOGY_VERSION}",
        f"// schema version   : {M.SCHEMA_VERSION}",
        f"// node labels      : {len(labels)}",
        f"// relationship types: {len(list(M.EdgeType))}",
        "//",
        "// GENERATED FILE - produced by generate_schema.py from "
        "learner_graph_models.py.",
        "// Edit the models (or DDL_SPEC) and regenerate; do not hand-edit this file.",
        "//",
        "// Every statement uses IF NOT EXISTS, so this script is idempotent and safe",
        "// to re-run on an existing database.",
        "//",
        "// EDITION SUPPORT",
        "//   Sections 1-4 run on Neo4j 5.x Community AND Enterprise.",
        "//   Section 5 (property existence + node keys) is ENTERPRISE ONLY and is",
        "//   commented out. On Community the Pydantic models enforce required",
        "//   properties at write time instead.",
        "",
        "",
    ]

    # -- 1. primary key uniqueness -----------------------------------------
    L += _banner("1. Primary key uniqueness  (Community + Enterprise)")
    L += [
        "// Every node is keyed by a deterministic UUIDv5. Together with MERGE this",
        "// is what makes re-running the backfill a no-op instead of a duplication.",
        "",
    ]
    for label in labels:
        L.append(
            f"CREATE CONSTRAINT {_cname(label, 'id_unique')} IF NOT EXISTS\n"
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE;"
        )
    L.append("")

    # -- 2. business key uniqueness ----------------------------------------
    L += _banner("2. Business key uniqueness  (Community + Enterprise)")
    L += [
        "// Guards against the same real-world entity being minted twice under two",
        "// different ids - the failure mode that fragments a learner profile.",
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

    # -- 3. range indexes ---------------------------------------------------
    L += _banner("3. Range indexes on hot query paths  (Community + Enterprise)")
    L += [
        "// Chosen for the filters Epic 2 and Epic 3 actually run: scope by round,",
        "// filter by evidence type/strength, sort by recency.",
        "",
    ]
    for label in labels:
        for prop in DDL_SPEC[label]["indexes"]:
            L.append(
                f"CREATE INDEX {_iname(label, prop)} IF NOT EXISTS\n"
                f"FOR (n:{label}) ON (n.{prop});"
            )
    L.append("")
    L += ["// Relationship property indexes (Neo4j 5.x).", ""]
    for rel, prop in REL_INDEXES:
        L.append(
            f"CREATE INDEX rel_{rel.lower()}_{prop} IF NOT EXISTS\n"
            f"FOR ()-[r:{rel}]-() ON (r.{prop});"
        )
    L.append("")

    # -- 4. full-text indexes ----------------------------------------------
    L += _banner("4. Full-text indexes  (Community + Enterprise)")
    L += [
        "// Feeds the hybrid retrieval in Sprint 3: graph filtering narrows the",
        "// population, full-text search ranks the evidence inside it.",
        "",
    ]
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

    # -- 5. existence constraints (Enterprise) ------------------------------
    L += _banner("5. Property existence constraints  (ENTERPRISE ONLY - commented out)")
    L += [
        "// Neo4j Community rejects these with:",
        "//   'Property existence constraint requires Neo4j Enterprise Edition'",
        "//",
        "// Uncomment the whole section when running against Enterprise. The required",
        "// properties below are derived automatically from the Pydantic models, so",
        "// they stay in step with the Python contract.",
        "",
    ]
    for label in labels:
        cls = M.NODE_CLASSES[label]
        props = required_neo4j_properties(cls)
        if not props:
            continue
        L.append(f"// --- {label} ---")
        for prop in props:
            L.append(
                f"// CREATE CONSTRAINT {_cname(label, f'{prop}_exists')} IF NOT "
                f"EXISTS\n"
                f"// FOR (n:{label}) REQUIRE n.{prop} IS NOT NULL;"
            )
        L.append("")

    L += [
        "// Relationship property existence (ENTERPRISE ONLY).",
        "// Enforces that graded criterion results always carry a verdict and a",
        "// confidence - the Evidence-First rule applied at the relationship level.",
        "//",
        "// CREATE CONSTRAINT rel_scored_criterion_status_exists IF NOT EXISTS",
        "// FOR ()-[r:SCORED_CRITERION]-() REQUIRE r.status IS NOT NULL;",
        "// CREATE CONSTRAINT rel_scored_criterion_confidence_exists IF NOT EXISTS",
        "// FOR ()-[r:SCORED_CRITERION]-() REQUIRE r.confidence IS NOT NULL;",
        "",
    ]

    # -- 6. verification ----------------------------------------------------
    L += _banner("6. Verification queries  (run manually after loading the seed)")
    L += [
        "// 6a. What got created.",
        "// SHOW CONSTRAINTS;",
        "// SHOW INDEXES;",
        "",
        "// 6b. EVIDENCE-FIRST INVARIANTS. Each of these must return ZERO rows.",
        "//     They are the database-side mirror of LearnerGraph._evidence_first.",
        "",
        "// (i) no skill claim without supporting evidence",
        "// MATCH (a:SkillAssertion)",
        "// WHERE a.status <> 'no_evidence' AND NOT "
        "(a)-[:SUPPORTED_BY_EVIDENCE]->(:Evidence)",
        "// RETURN a.id AS unsupported_assertion, a.status;",
        "",
        "// (ii) no evidence without a traceable source record",
        "// MATCH (e:Evidence) WHERE NOT (e)-[:DERIVED_FROM]->() RETURN e.id AS "
        "untraceable;",
        "",
        "// (iii) no evidence detached from a learner",
        "// MATCH (e:Evidence) WHERE NOT (e)-[:EVIDENCE_FOR_LEARNER]->(:Learner)",
        "// RETURN e.id AS orphan_evidence;",
        "",
        "// (iv) no behavioural observation without evidence",
        "// MATCH (o:Observation) WHERE NOT (o)-[:SUPPORTED_BY_EVIDENCE]->(:Evidence)",
        "// RETURN o.id AS unsupported_observation;",
        "",
        "// (v) provenance coverage must be 100% (PRD success metric)",
        "// MATCH (e:Evidence)",
        "// WHERE e.source_system IS NULL OR e.source_id IS NULL OR "
        "e.source_observed_at IS NULL",
        "// RETURN e.id AS missing_provenance;",
        "",
        "// 6c. IDEMPOTENCY CHECK. Record the counts, re-run sample_learner_seed.cql,",
        "//     then re-run this: the numbers must be identical.",
        "// MATCH (n) RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label;",
        "// MATCH ()-[r]->() RETURN type(r) AS rel, count(*) AS rels ORDER BY rel;",
        "",
        "// 6d. THE DEMO TRAVERSAL - 'Does this learner know Python? Show the "
        "evidence.'",
        "// MATCH (l:Learner {canonical_email: 'learner-a4@example.invalid'})",
        "//       -[:HAS_SKILL_ASSERTION]->(a:SkillAssertion)-[:ABOUT_SKILL]->(s:Skill "
        "{slug: 'python'})",
        "// MATCH (a)-[:SUPPORTED_BY_EVIDENCE]->(e:Evidence)",
        "// RETURN s.canonical_name AS skill, a.tier AS tier, a.status AS strength,",
        "//        e.evidence_type AS type, e.source_system AS source,",
        "//        e.observed_at AS observed, e.title AS evidence",
        "// ORDER BY e.observed_at DESC;",
        "",
        "// 6e. EVIDENCE COVERAGE per learner - PRD 8.2 fairness guard, so a",
        "//     heavily-observed learner is not mistaken for a stronger one.",
        "// MATCH (e:Evidence)-[:EVIDENCE_FOR_LEARNER]->(l:Learner)",
        "// RETURN l.display_name AS learner, count(e) AS evidence_items,",
        "//        count(DISTINCT e.source_system) AS distinct_sources",
        "// ORDER BY evidence_items DESC;",
    ]

    return "\n".join(L).rstrip() + "\n"


def _cname(label: str, suffix: str) -> str:
    return f"c_{label.lower()}_{suffix}"


def _iname(label: str, prop: str) -> str:
    return f"i_{label.lower()}_{prop}"


def _statements(text: str) -> list[str]:
    """Split a generated .cql body into individual active statements."""
    out: list[str] = []
    for raw in text.split(";"):
        stmt = "\n".join(
            ln
            for ln in raw.splitlines()
            if ln.strip() and not ln.strip().startswith("//")
        ).strip()
        if stmt:
            out.append(stmt)
    return out


def _render_list(name: str, stmts: list[str], doc: str) -> str:
    lines = [f"#: {doc}", f"{name}: list[str] = ["]
    for stmt in stmts:
        body = "\n".join("    " + ln.strip() for ln in stmt.splitlines())
        lines.append('    """')
        lines.append(body)
        lines.append('    """,')
    lines.append("]")
    return "\n".join(lines)


def build_python() -> str:
    """Emit src/app/graph/constraints.py in the project's existing style.

    The repo already expresses Neo4j DDL as Python lists of Cypher strings
    (see the original placeholder). Keeping that shape means the ingestion
    loader can simply iterate the lists, and nothing has to parse a .cql file
    at runtime.
    """
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
    for rel, prop in REL_INDEXES:
        indexes.append(
            f"CREATE INDEX rel_{rel.lower()}_{prop} IF NOT EXISTS\n"
            f"FOR ()-[r:{rel}]-() ON (r.{prop})"
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

    enterprise: list[str] = []
    for label in labels:
        for prop in required_neo4j_properties(M.NODE_CLASSES[label]):
            enterprise.append(
                f"CREATE CONSTRAINT {_cname(label, prop + '_exists')} IF NOT EXISTS\n"
                f"FOR (n:{label}) REQUIRE n.{prop} IS NOT NULL"
            )

    header = f'''"""
Neo4j constraints and indexes for the Professional Learner Graph.

GENERATED FILE - produced by ``scripts/generate_constraints.py`` from
``src/app/graph/schema.py``. Do not hand-edit; change the models and
regenerate so the database rules cannot drift from the Python contract.

Every statement uses ``IF NOT EXISTS``, so applying these repeatedly is safe.

EDITION SUPPORT
    ``CONSTRAINTS``, ``INDEXES`` and ``FULLTEXT_INDEXES`` run on Neo4j 5.x
    Community AND Enterprise.

    ``ENTERPRISE_ONLY_CONSTRAINTS`` are property-existence constraints, which
    Community Edition rejects. Apply them only on Enterprise; on Community the
    Pydantic models in ``schema.py`` are the enforcement layer for required
    properties.

ontology version : {M.ONTOLOGY_VERSION}
node labels      : {len(labels)}
"""

'''

    parts = [
        header,
        _render_list(
            "CONSTRAINTS",
            constraints,
            "Uniqueness constraints. Community + Enterprise.",
        ),
        "",
        _render_list(
            "INDEXES",
            indexes,
            "Range indexes on the hot Epic 2/3 filter paths. Community + Enterprise.",
        ),
        "",
        _render_list(
            "FULLTEXT_INDEXES",
            fulltext,
            "Full-text indexes feeding Sprint 3 hybrid retrieval.",
        ),
        "",
        _render_list(
            "ENTERPRISE_ONLY_CONSTRAINTS",
            enterprise,
            "Property existence constraints. ENTERPRISE ONLY - Community rejects "
            "these.",
        ),
        "",
        "#: Everything safe to apply on any Neo4j 5.x edition, in order.",
        "ALL_STATEMENTS: list[str] = CONSTRAINTS + INDEXES + FULLTEXT_INDEXES",
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

    OUT_CQL.parent.mkdir(parents=True, exist_ok=True)
    OUT_CQL.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT_CQL.relative_to(ROOT)}")

    if args.write_module:
        OUT_PY.parent.mkdir(parents=True, exist_ok=True)
        OUT_PY.write_text(build_python(), encoding="utf-8")
        print(f"wrote {OUT_PY.relative_to(ROOT)}")
    else:
        print(
            "skipped src/app/graph/constraints.py (owned by the integration "
            "workstream) - pass --write-module to generate it"
        )
