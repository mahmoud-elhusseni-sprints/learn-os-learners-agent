"""
Test suite for the Professional Learner Graph ontology.

Runs under pytest (``pytest test_learner_graph.py``) or standalone
(``python3 test_learner_graph.py``) so it works before the team has agreed a
dev-dependency set.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import src.app.graph.schema as M
import src.app.graph.serialization as CE
from scripts import generate_constraints as GS
from src.app.graph.ids import (
    SPRINTS_GRAPH_NAMESPACE,
    assertion_uid,
    composite_key,
    deterministic_id,
    skill_uid,
)

HERE = Path(__file__).parent
NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def _prov(**kw):
    base = dict(
        source_system=M.SourceSystem.LMS,
        source_id="s1",
        source_type="t",
        observed_at=NOW,
        ingested_at=NOW,
    )
    base.update(kw)
    return M.Provenance(**base)


def _learner(email="a@example.invalid"):
    return M.Learner(
        id=deterministic_id("vi", "learner", email),
        created_at=NOW,
        provenance=_prov(),
        canonical_email=email,
        display_name="A",
    )


def _skill(slug="python"):
    return M.Skill(
        id=skill_uid(slug),
        created_at=NOW,
        canonical_name=slug.title(),
        slug=slug,
        category=M.SkillCategory.DIGITAL_AI_SKILLS,
    )


def _evidence(n=1, **kw):
    base = dict(
        id=deterministic_id("vi", "evidence", str(n)),
        created_at=NOW,
        provenance=_prov(source_id=f"e{n}"),
        evidence_type=M.EvidenceType.DELIVERED_WORK,
        strength=M.EvidenceStrength.HIGH,
        title="t",
        content="c",
        observed_at=NOW,
    )
    base.update(kw)
    return M.Evidence(**base)


def _edge(t, src, dst, **props):
    return M.Edge(
        type=t,
        source_label=src.label,
        source_id=src.id,
        target_label=dst.label,
        target_id=dst.id,
        properties=props,
    )


# ---------------------------------------------------------------- identifiers


def test_namespace_is_reproducible():
    assert SPRINTS_GRAPH_NAMESPACE == uuid.uuid5(uuid.NAMESPACE_DNS, "graph.sprints.ai")


def test_ids_are_deterministic_and_v5():
    a = deterministic_id("vi", "lx", "abc")
    assert a == deterministic_id("vi", "lx", "abc")
    assert a.version == 5
    assert a != deterministic_id("vi", "lx", "abd")


def test_composite_key_is_collision_safe():
    assert composite_key("ab", "c") != composite_key("a", "bc")


def test_assertion_id_keys_on_learner_skill_tier():
    lid, sid = deterministic_id("vi", "learner", "1"), skill_uid("python")
    assert assertion_uid(lid, sid, "assessed") == assertion_uid(lid, sid, "assessed")
    assert assertion_uid(lid, sid, "assessed") != assertion_uid(
        lid, sid, "demonstrated"
    )


# ------------------------------------------------------------------ timestamps


def test_naive_timestamp_rejected():
    try:
        _prov(observed_at=datetime(2026, 8, 31))
    except Exception as e:
        assert "timezone-aware" in str(e)
    else:
        raise AssertionError("naive datetime was accepted")


def test_non_utc_offset_normalised_to_utc():
    p = _prov(observed_at="2026-07-21T23:33:14+03:00")
    assert p.observed_at.utcoffset().total_seconds() == 0
    assert p.observed_at.hour == 20


def test_z_suffix_parsed():
    assert _prov(observed_at="2026-07-21T20:33:14.676Z").observed_at.year == 2026


# ---------------------------------------------------------------------- models


def test_extra_properties_forbidden():
    try:
        M.Skill(
            id=skill_uid("k"),
            created_at=NOW,
            canonical_name="K",
            slug="k",
            category=M.SkillCategory.WORK_SKILLS,
            typo_field=1,
        )
    except Exception as e:
        assert "extra" in str(e).lower()
    else:
        raise AssertionError("unknown property accepted")


def test_evidence_requires_provenance():
    try:
        M.Evidence(
            id=deterministic_id("x", "y", "1"),
            created_at=NOW,
            evidence_type=M.EvidenceType.DELIVERED_WORK,
            strength=M.EvidenceStrength.HIGH,
            title="t",
            content="c",
            observed_at=NOW,
        )
    except Exception as e:
        assert "provenance" in str(e)
    else:
        raise AssertionError("Evidence without provenance accepted")


def test_assertion_status_must_match_evidence_count():
    for status, count in (
        (M.AssertionStatus.STRONG, 0),
        (M.AssertionStatus.NO_EVIDENCE, 2),
    ):
        try:
            M.SkillAssertion(
                id=deterministic_id("x", "y", str(count)),
                created_at=NOW,
                computed_at=NOW,
                computed_by="t@1",
                tier=M.SkillEvidenceTier.DEMONSTRATED,
                status=status,
                evidence_count=count,
            )
        except Exception:
            pass
        else:
            raise AssertionError(f"{status} with evidence_count={count} accepted")


def test_no_evidence_state_is_representable():
    a = M.SkillAssertion(
        id=deterministic_id("x", "y", "ok"),
        created_at=NOW,
        computed_at=NOW,
        computed_by="t@1",
        tier=M.SkillEvidenceTier.DEMONSTRATED,
        status=M.AssertionStatus.NO_EVIDENCE,
        evidence_count=0,
    )
    assert a.status is M.AssertionStatus.NO_EVIDENCE


def test_observation_rejects_personality_labels():
    try:
        M.Observation(
            id=deterministic_id("x", "y", "o"),
            created_at=NOW,
            computed_at=NOW,
            computed_by="t@1",
            category=M.ObservationCategory.COLLABORATION,
            context="sprint",
            behavior="learner was lazy about it",
            observed_at=NOW,
        )
    except Exception as e:
        assert "personality label" in str(e)
    else:
        raise AssertionError("personality label accepted")


def test_observation_accepts_behavioural_description():
    o = M.Observation(
        id=deterministic_id("x", "y", "o2"),
        created_at=NOW,
        computed_at=NOW,
        computed_by="t@1",
        category=M.ObservationCategory.ADAPTABILITY,
        context="standup 2026-07-27",
        behavior="adapted his approach when the company API became unavailable",
        observed_at=NOW,
    )
    assert o.category is M.ObservationCategory.ADAPTABILITY


def test_career_goal_unknown_state():
    g = M.CareerGoal(
        id=deterministic_id("x", "y", "g"),
        created_at=NOW,
        provenance=_prov(),
        status=M.CareerGoalStatus.UNKNOWN,
    )
    assert g.target_role is None


# ----------------------------------------------------------------------- edges


def test_illegal_edge_direction_rejected():
    try:
        M.Edge(
            type=M.EdgeType.DEMONSTRATED_SKILL,
            source_label="Skill",
            source_id=skill_uid("python"),
            target_label="Learner",
            target_id=deterministic_id("x", "y", "l"),
        )
    except Exception as e:
        assert "illegal relationship" in str(e)
    else:
        raise AssertionError("reversed edge accepted")


def test_edge_properties_validated_against_spec():
    learner, s = _learner(), _skill()
    try:
        _edge(
            M.EdgeType.DEMONSTRATED_SKILL,
            learner,
            s,
            assertion_id="not-a-uuid",
            status="strong",
        )
    except Exception:
        pass
    else:
        raise AssertionError("bad edge property accepted")


def test_edge_without_property_model_rejects_properties():
    learner = _learner()
    lx = M.LearningExperience(
        id=deterministic_id("vi", "lx", "1"),
        created_at=NOW,
        provenance=_prov(),
        lx_key="1",
        status=M.LXStatus.ACTIVE,
    )
    try:
        _edge(M.EdgeType.HAS_LEARNING_EXPERIENCE, learner, lx, weight=3)
    except Exception as e:
        assert "takes no properties" in str(e)
    else:
        raise AssertionError("unexpected properties accepted")


def test_every_edge_type_has_at_least_one_spec():
    covered = {s.type for s in M.EDGE_SPECS}
    assert covered == set(M.EdgeType), sorted(
        t.value for t in set(M.EdgeType) - covered
    )


# ----------------------------------------------------------------- graph rules


def _minimal_supported_graph():
    learner, s, ev = _learner(), _skill(), _evidence()
    a = M.SkillAssertion(
        id=assertion_uid(learner.id, s.id, "demonstrated"),
        created_at=NOW,
        computed_at=NOW,
        computed_by="t@1",
        tier=M.SkillEvidenceTier.DEMONSTRATED,
        status=M.AssertionStatus.WEAK,
        evidence_count=1,
    )
    sub = M.Submission(
        id=deterministic_id("vi", "submission", "1"),
        created_at=NOW,
        provenance=_prov(),
        kind="link",
    )
    return M.LearnerGraph(
        generated_at=NOW,
        nodes=[learner, s, ev, a, sub],
        edges=[
            _edge(M.EdgeType.HAS_SKILL_ASSERTION, learner, a),
            _edge(M.EdgeType.ABOUT_SKILL, a, s),
            _edge(M.EdgeType.SUPPORTED_BY_EVIDENCE, a, ev),
            _edge(M.EdgeType.EVIDENCE_FOR_LEARNER, ev, learner),
            _edge(M.EdgeType.DERIVED_FROM, ev, sub),
        ],
    )


def test_minimal_evidence_backed_graph_is_valid():
    g = _minimal_supported_graph()
    assert len(g.nodes) == 5


def test_unsupported_claim_rejected_at_graph_level():
    g = _minimal_supported_graph()
    nodes = list(g.nodes)
    edges = [e for e in g.edges if e.type is not M.EdgeType.SUPPORTED_BY_EVIDENCE]
    try:
        M.LearnerGraph(generated_at=NOW, nodes=nodes, edges=edges)
    except Exception as e:
        assert "Evidence-First" in str(e)
    else:
        raise AssertionError("unsupported claim accepted")


def test_untraceable_evidence_rejected():
    g = _minimal_supported_graph()
    edges = [e for e in g.edges if e.type is not M.EdgeType.DERIVED_FROM]
    try:
        M.LearnerGraph(generated_at=NOW, nodes=list(g.nodes), edges=edges)
    except Exception as e:
        assert "no DERIVED_FROM" in str(e)
    else:
        raise AssertionError("untraceable evidence accepted")


def test_dangling_edge_rejected():
    learner, s = _learner(), _skill()
    try:
        M.LearnerGraph(
            generated_at=NOW,
            nodes=[learner],
            edges=[
                _edge(
                    M.EdgeType.DEMONSTRATED_SKILL,
                    learner,
                    s,
                    assertion_id=str(learner.id),
                    status=M.AssertionStatus.WEAK.value,
                )
            ],
        )
    except Exception as e:
        assert "dangling" in str(e)
    else:
        raise AssertionError("dangling edge accepted")


def test_duplicate_node_ids_rejected():
    learner = _learner()
    try:
        M.LearnerGraph(
            generated_at=NOW, nodes=[learner, learner.model_copy()], edges=[]
        )
    except Exception as e:
        assert "duplicate node ids" in str(e)
    else:
        raise AssertionError("duplicate ids accepted")


def test_cardinality_violation_rejected():
    """HAS_CAREER_GOAL is 1:1 - two goals for one learner must fail."""
    learner = _learner()
    goals = [
        M.CareerGoal(
            id=deterministic_id("p", "goal", str(i)),
            created_at=NOW,
            provenance=_prov(),
            status=M.CareerGoalStatus.UNKNOWN,
        )
        for i in (1, 2)
    ]
    try:
        M.LearnerGraph(
            generated_at=NOW,
            nodes=[learner, *goals],
            edges=[_edge(M.EdgeType.HAS_CAREER_GOAL, learner, g) for g in goals],
        )
    except Exception as e:
        assert "cardinality" in str(e)
    else:
        raise AssertionError("cardinality violation accepted")


# --------------------------------------------------------------------- fixture


def _fixture():
    return M.LearnerGraph.model_validate(
        json.loads(
            (HERE / "fixtures" / "sample_learner_seed.json").read_text(encoding="utf-8")
        )
    )


def test_fixture_validates():
    g = _fixture()
    assert len(g.nodes) > 100 and len(g.edges) > 100


def test_fixture_has_multi_source_evidence():
    g = _fixture()
    systems = {e.provenance.source_system for e in g.by_label("Evidence")}
    assert len(systems) >= 3, systems


def test_fixture_has_all_four_evidence_classes_represented():
    g = _fixture()
    types = {e.evidence_type for e in g.by_label("Evidence")}
    assert len(types) >= 4, types


def test_fixture_contains_an_evidence_gap():
    g = _fixture()
    gaps = [
        a
        for a in g.by_label("SkillAssertion")
        if a.status is M.AssertionStatus.NO_EVIDENCE
    ]
    assert gaps
    for gap in gaps:
        assert not g.edges_of(M.EdgeType.SUPPORTED_BY_EVIDENCE, source_id=gap.id)


def test_fixture_tiers_are_distinguished():
    g = _fixture()
    tiers = {a.tier for a in g.by_label("SkillAssertion")}
    assert len(tiers) >= 2, tiers


def test_fixture_provenance_coverage_is_total():
    g = _fixture()
    for n in g.nodes:
        if isinstance(n, M.SourceNode):
            assert n.provenance.source_id and n.provenance.observed_at


def test_fixture_carries_no_leaked_github_handle():
    raw = (HERE / "fixtures" / "sample_learner_seed.json").read_text(encoding="utf-8")
    assert "MoHatemTC" not in raw


# ---------------------------------------------------------------- cypher export


def test_export_is_merge_only():
    cql = CE.export_graph(_fixture())
    body = "\n".join(ln for ln in cql.splitlines() if not ln.strip().startswith("//"))
    assert "CREATE" not in body
    assert "MERGE" in body


def test_export_is_byte_stable():
    g = _fixture()
    assert CE.export_graph(g) == CE.export_graph(g)


def test_export_escapes_quotes_and_newlines():
    assert CE.cypher_literal("it's\nfine") == r"'it\'s\nfine'"


def test_export_renders_timestamps_as_temporal_type():
    assert CE.cypher_literal("2026-07-21T20:33:14+00:00", "observed_at").startswith(
        "datetime("
    )
    assert CE.cypher_literal("not a date", "title") == "'not a date'"


def test_provenance_is_flattened_without_collision():
    g = _fixture()
    ev = next(iter(g.by_label("Evidence")))
    flat = CE.flatten_node(ev)
    assert "provenance" not in flat
    assert flat["source_system"] and flat["source_observed_at"]
    # Evidence.observed_at must survive alongside provenance.observed_at
    assert flat["observed_at"] and flat["observed_at"] != flat.get("ingested_at")


# ----------------------------------------------------------------------- schema


def test_ddl_covers_every_node_label():
    assert set(GS.DDL_SPEC) == set(M.NODE_CLASSES)


def _generated() -> dict[str, list[str]]:
    """Statements produced by the generator.

    Tests target the generated specification, not src/app/graph/constraints.py -
    that module is owned by the Neo4j/integration workstream, which decides when
    to regenerate it.
    """
    ns: dict[str, object] = {}
    exec(GS.build_python(), ns)  # noqa: S102 - our own generated source
    return {
        k: list(ns[k])
        for k in (
            "CONSTRAINTS",
            "INDEXES",
            "FULLTEXT_INDEXES",
            "ENTERPRISE_ONLY_CONSTRAINTS",
            "ALL_STATEMENTS",
        )
    }


def test_ddl_is_idempotent_and_community_safe():
    gen = _generated()
    assert gen["ALL_STATEMENTS"], "no statements generated"
    for stmt in gen["ALL_STATEMENTS"]:
        assert "IF NOT EXISTS" in stmt, stmt
    body = "\n".join(gen["ALL_STATEMENTS"])
    assert "IS NOT NULL" not in body, "existence constraint leaked into the safe set"
    assert "IS NODE KEY" not in body, "node key constraint leaked into the safe set"


def test_enterprise_constraints_are_kept_separate():
    gen = _generated()
    assert gen["ENTERPRISE_ONLY_CONSTRAINTS"]
    for stmt in gen["ENTERPRISE_ONLY_CONSTRAINTS"]:
        assert "IS NOT NULL" in stmt


def test_ddl_has_a_uniqueness_constraint_per_label():
    body = "\n".join(_generated()["CONSTRAINTS"])
    for label in M.NODE_CLASSES:
        assert f"FOR (n:{label}) REQUIRE n.id IS UNIQUE" in body, label


def test_cql_deliverable_is_in_sync_with_the_models():
    """docs/data/schema_constraints.cql is this task's DDL deliverable."""
    cql_path = HERE.parent / "docs" / "data" / "schema_constraints.cql"
    cql = cql_path.read_text(encoding="utf-8")
    assert cql == GS.build(), (
        "docs/data/schema_constraints.cql is stale - "
        "run: python3 scripts/generate_constraints.py"
    )


def test_required_properties_derive_from_models():
    req = CE.required_neo4j_properties(M.Evidence)
    for prop in (
        "id",
        "content",
        "evidence_type",
        "strength",
        "source_system",
        "source_id",
        "source_observed_at",
    ):
        assert prop in req, prop


# ------------------------------------------------------------------- standalone

if __name__ == "__main__":
    tests = [
        (n, o)
        for n, o in sorted(globals().items())
        if n.startswith("test_") and callable(o)
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as exc:  # noqa: BLE001
            failed.append((name, exc))
            print(f"  FAIL  {name}: {exc}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} tests passed")
    raise SystemExit(1 if failed else 0)
