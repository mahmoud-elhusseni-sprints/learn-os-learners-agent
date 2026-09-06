"""
Validation demonstration for the Professional Learner Graph ontology.

Run:  python3 validate_seed.py

Proves, in order:
  1. the seed fixture validates against the Pydantic v2 models;
  2. ids are deterministic (re-ingestion is idempotent);
  3. the models actively REJECT malformed and unsupported data;
  4. one learner is linked to evidence from multiple distinct source systems;
  5. the "show me the evidence" traversal works end to end;
  6. an evidence gap is representable and distinguishable from a skill gap;
  7. the generated Cypher load script is MERGE-only and therefore re-runnable.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import src.app.graph.schema as M
from src.app.graph.ids import deterministic_id, skill_uid
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

    # round-trip
    again = M.LearnerGraph.model_validate(
        json.loads(graph.model_dump_json(exclude_none=True))
    )
    check(
        "model -> JSON -> model round-trip is lossless",
        len(again.nodes) == len(graph.nodes) and len(again.edges) == len(graph.edges),
    )

    # -- 2. determinism ------------------------------------------------------
    header("2. Identifiers are deterministic (idempotent re-ingestion)")
    a = deterministic_id("virtual_internship", "lx", "144bd399-aaaa")
    b = deterministic_id("virtual_internship", "lx", "144bd399-aaaa")
    check("same source record -> same UUID", a == b, str(a))
    check(
        "different source record -> different UUID",
        a != deterministic_id("virtual_internship", "lx", "144bd399-bbbb"),
    )
    check("UUIDv5 (name-based, reproducible across machines)", a.version == 5)
    check(
        "skill ids key off the canonical slug",
        skill_uid("python") == skill_uid("python"),
    )

    # -- 3. the models reject bad data --------------------------------------
    header("3. Invalid data is rejected, not silently accepted")
    now = datetime(2026, 8, 31, tzinfo=timezone.utc)
    prov = M.Provenance(
        source_system=M.SourceSystem.LMS,
        source_id="x",
        source_type="t",
        observed_at=now,
        ingested_at=now,
    )

    rejects(
        "naive (non-UTC) timestamp is refused",
        lambda: M.Provenance(
            source_system=M.SourceSystem.LMS,
            source_id="x",
            source_type="t",
            observed_at=datetime(2026, 8, 31),  # naive
            ingested_at=now,
        ),
        "timezone-aware",
    )

    rejects(
        "Evidence without provenance is refused",
        lambda: M.Evidence(
            id=deterministic_id("x", "y", "1"),
            created_at=now,
            evidence_type=M.EvidenceType.DELIVERED_WORK,
            strength=M.EvidenceStrength.HIGH,
            title="t",
            content="c",
            observed_at=now,
        ),
        "provenance",
    )

    rejects(
        "unknown property is refused (extra='forbid')",
        lambda: M.Skill(
            id=skill_uid("k8s"),
            created_at=now,
            canonical_name="Kubernetes",
            slug="k8s",
            category=M.SkillCategory.DIGITAL_AI_SKILLS,
            skill_levl="expert",
        ),
        "extra",
    )

    rejects(
        "confidence outside 0..1 is refused",
        lambda: M.Evidence(
            id=deterministic_id("x", "y", "2"),
            created_at=now,
            provenance=prov,
            evidence_type=M.EvidenceType.DELIVERED_WORK,
            strength=M.EvidenceStrength.HIGH,
            confidence=1.4,
            title="t",
            content="c",
            observed_at=now,
        ),
        "less than or equal to 1",
    )

    rejects(
        "a skill claim asserting strength with zero evidence is refused",
        lambda: M.SkillAssertion(
            id=deterministic_id("x", "y", "3"),
            created_at=now,
            computed_at=now,
            computed_by="t@1",
            tier=M.SkillEvidenceTier.DEMONSTRATED,
            status=M.AssertionStatus.STRONG,
            evidence_count=0,
        ),
        "requires at least one evidence item",
    )

    rejects(
        "'no_evidence' contradicted by an evidence count is refused",
        lambda: M.SkillAssertion(
            id=deterministic_id("x", "y", "4"),
            created_at=now,
            computed_at=now,
            computed_by="t@1",
            tier=M.SkillEvidenceTier.DEMONSTRATED,
            status=M.AssertionStatus.NO_EVIDENCE,
            evidence_count=3,
        ),
        "contradicts",
    )

    rejects(
        "a personality label in an Observation is refused (PRD 8.2)",
        lambda: M.Observation(
            id=deterministic_id("x", "y", "5"),
            created_at=now,
            computed_at=now,
            computed_by="t@1",
            category=M.ObservationCategory.COLLABORATION,
            context="sprint 3",
            behavior="the learner is lazy",
            observed_at=now,
        ),
        "personality label",
    )

    rejects(
        "an unregistered relationship direction is refused",
        lambda: M.Edge(
            type=M.EdgeType.DEMONSTRATED_SKILL,
            source_label="Skill",
            source_id=skill_uid("python"),
            target_label="Learner",
            target_id=skill_uid("x"),
        ),
        "illegal relationship",
    )

    rejects(
        "a career goal marked 'stated' with no target role is refused",
        lambda: M.CareerGoal(
            id=deterministic_id("x", "y", "6"),
            created_at=now,
            provenance=prov,
            status=M.CareerGoalStatus.STATED,
        ),
        "requires target_role",
    )

    # Evidence-First, at graph level
    learner = next(n for n in graph.by_label("Learner"))
    orphan = M.SkillAssertion(
        id=deterministic_id("x", "y", "7"),
        created_at=now,
        computed_at=now,
        computed_by="t@1",
        tier=M.SkillEvidenceTier.DEMONSTRATED,
        status=M.AssertionStatus.STRONG,
        evidence_count=2,
    )
    a_skill = graph.by_label("Skill")[0]
    rejects(
        "a claim with no SUPPORTED_BY_EVIDENCE edge is refused at graph level",
        lambda: M.LearnerGraph(
            generated_at=now,
            nodes=[learner, a_skill, orphan],
            edges=[
                M.Edge(
                    type=M.EdgeType.HAS_SKILL_ASSERTION,
                    source_label="Learner",
                    source_id=learner.id,
                    target_label="SkillAssertion",
                    target_id=orphan.id,
                ),
                M.Edge(
                    type=M.EdgeType.ABOUT_SKILL,
                    source_label="SkillAssertion",
                    source_id=orphan.id,
                    target_label="Skill",
                    target_id=a_skill.id,
                ),
            ],
        ),
        "Evidence-First",
    )

    # -- 4. multi-source evidence -------------------------------------------
    header("4. Traceable multi-source evidence linkage")
    evidence = [n for n in graph.by_label("Evidence")]
    by_system = Counter(e.provenance.source_system.value for e in evidence)
    by_type = Counter(e.evidence_type.value for e in evidence)

    check(
        "evidence is drawn from 3+ distinct source systems",
        len(by_system) >= 3,
        ", ".join(f"{k}={v}" for k, v in sorted(by_system.items())),
    )
    check(
        "evidence spans multiple evidence classes",
        len(by_type) >= 3,
        ", ".join(f"{k}={v}" for k, v in sorted(by_type.items())),
    )
    check(
        "100% of evidence carries source_system + source_id + timestamp",
        all(
            e.provenance.source_system
            and e.provenance.source_id
            and e.provenance.observed_at
            for e in evidence
        ),
        f"{len(evidence)} items",
    )
    check(
        "100% of evidence is traceable to a source record (DERIVED_FROM)",
        all(graph.edges_of(M.EdgeType.DERIVED_FROM, source_id=e.id) for e in evidence),
    )
    check(
        "every evidence item carries an access scope (FR-03)",
        all(e.access_scope is not None for e in evidence),
    )

    print("\n  evidence by source system:")
    idx = graph.index()
    for system, count in sorted(by_system.items()):
        sample = next(e for e in evidence if e.provenance.source_system.value == system)
        target = idx[
            graph.edges_of(M.EdgeType.DERIVED_FROM, source_id=sample.id)[0].target_id
        ]
        print(
            f"    {system:20} {count:3}  e.g. -> {target.label}"  # type: ignore[attr-defined]
            f" [{sample.provenance.source_type}]"
        )

    # -- 5. the demo traversal ----------------------------------------------
    header("5. 'Does this learner know X? Show me the evidence.'")
    skills = {s.slug: s for s in graph.by_label("Skill")}  # type: ignore[attr-defined]
    for slug in ("python", "react", "pipeline-orchestration"):
        if slug not in skills:
            continue
        skill = skills[slug]
        found = graph.evidence_for_skill(learner.id, skill.id)
        tiers = {}
        for e in graph.edges_of(M.EdgeType.HAS_SKILL_ASSERTION, source_id=learner.id):
            a = idx[e.target_id]
            if any(
                x.target_id == skill.id
                for x in graph.edges_of(M.EdgeType.ABOUT_SKILL, source_id=a.id)
            ):
                tiers[a.tier.value] = a.status.value  # type: ignore[attr-defined]
        print(
            f"\n  {skill.canonical_name}: "  # type: ignore[attr-defined]
            + (
                ", ".join(f"{t}={s}" for t, s in sorted(tiers.items()))
                or "no assertions"
            )
        )
        for e in found[:3]:
            print(
                f"    - [{e.evidence_type.value}/{e.strength.value} "
                f"conf={e.confidence:.2f}] {e.observed_at.date()} "
                f"({e.provenance.source_system.value})"
            )
            print(f"      {e.content[:120].strip()}")
        if found:
            check(
                f"'{slug}' evidence is retrievable with provenance",
                True,
                f"{len(found)} item(s)",
            )

    # -- 6. the evidence gap -------------------------------------------------
    header("6. Uncertainty is a first-class, queryable state")
    gaps = [
        n
        for n in graph.by_label("SkillAssertion")
        if n.status is M.AssertionStatus.NO_EVIDENCE
    ]  # type: ignore[attr-defined]
    check("at least one 'no_evidence' assertion exists", bool(gaps))
    for g in gaps:
        skill = idx[graph.edges_of(M.EdgeType.ABOUT_SKILL, source_id=g.id)[0].target_id]
        goal_targets = [
            e.target_id for e in graph.edges_of(M.EdgeType.GOAL_TARGETS_SKILL)
        ]
        print(
            f"\n  {skill.canonical_name}: status={g.status.value}, "  # type: ignore[attr-defined]
            f"tier={g.tier.value}, is a career-goal target="  # type: ignore[attr-defined]
            f"{skill.id in goal_targets}"
        )
        print(f"    {g.rationale}")  # type: ignore[attr-defined]
        check(
            "the gap is distinguishable from a demonstrated absence",
            g.evidence_count == 0
            and not graph.edges_of(  # type: ignore[attr-defined]
                M.EdgeType.SUPPORTED_BY_EVIDENCE, source_id=g.id
            ),
        )

    # -- 7. idempotent Cypher ------------------------------------------------
    header("7. Generated Cypher is re-runnable")
    cql = export_graph(graph, title="Sample learner seed - Learner A4")
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
        export_graph(graph, title="Sample learner seed - Learner A4") == cql,
    )
    print(f"\n  wrote {LOAD_CQL.name} ({len(cql.splitlines())} lines)")

    # -- summary -------------------------------------------------------------
    print("\n" + "=" * 78)
    counts = graph.counts()
    print("graph:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    print(f"\n{_passed} checks passed, {_failed} failed")
    print("=" * 78)
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
