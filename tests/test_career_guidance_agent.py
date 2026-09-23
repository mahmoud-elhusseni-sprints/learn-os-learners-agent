"""Offline tests for Task 22: Career Guidance Agent. The LLM is always mocked."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from src.app.agents.career_guidance import (
    CareerGuidanceAgent,
    CareerGuidanceError,
    LLMRecommendationWriter,
    RoleRegistry,
    UnknownRoleError,
)
from src.app.agents.career_guidance.__main__ import main
from src.app.agents.career_guidance.gap_analysis import assess_competencies
from src.app.agents.career_guidance.prompts import (
    ALLOWED_CATEGORIES,
    SYSTEM_PROMPT,
    build_recommendation_prompt,
)
from src.app.agents.career_guidance.recommendations import (
    MAX_RECOMMENDATIONS,
    RecommendationOutputError,
    choose_category,
    parse_recommendation_payload,
)
from src.app.agents.career_guidance.roles import AI_ENGINEER, DEFAULT_ROLE_REGISTRY
from src.app.schemas.career_guidance import (
    CareerGuidanceProfile,
    CareerGuidanceResult,
    CompetencyAssessment,
    CompetencyKind,
    EvidenceStatus,
    GapPriority,
    GenerationMode,
    Importance,
    ProficiencyLevel,
    ProfileCompleteness,
    Recommendation,
    RecommendationCategory,
    SkillGap,
)

EXAMPLE_REQUEST = (
    Path(__file__).resolve().parents[1] / "docs/examples/career_guidance_request.json"
)
AGENT_MODULE = "src.app.agents.career_guidance.agent"
NON_TECHNICAL_KEYS = {
    "technical_presentation",
    "collaboration",
    "feedback_assimilation",
}


def item(evidence_id, competencies=(), source="project", outcome="passed", **extra):
    return {
        "evidence_id": evidence_id,
        "source_type": source,
        "title": extra.pop("title", f"Work {evidence_id}"),
        "competencies": list(competencies),
        "outcome": outcome,
        **extra,
    }


def profile(**changes):
    return CareerGuidanceProfile.model_validate(
        {"target_role": "AI Engineer", **changes}
    )


def technically_strong():
    """Good technical evidence, no evidence of presenting, teamwork or feedback."""
    return profile(
        learner_id="learner-tech",
        skills=[{"name": "Python", "level": "advanced", "evidence_ids": ["ev-rag"]}],
        evidence=[
            item(
                "ev-rag",
                ["python", "rag pipelines", "machine learning", "apis"],
                title="Document Q&A RAG prototype",
            ),
            item(
                "ev-api",
                ["apis", "python", "software engineering", "testing"],
                source="review",
            ),
            item(
                "ev-ml",
                [
                    "machine learning",
                    "rag pipelines",
                    "software engineering",
                    "testing",
                ],
                source="assessment",
            ),
            item("ev-data", ["sql", "data analysis", "system design"]),
            item("ev-data-2", ["sql", "data analysis", "system design"], source="task"),
        ],
    )


def status_of(result, key):
    return next(a.status for a in result.assessments if a.competency_key == key)


def gap_keys(result):
    return {gap.competency_key for gap in result.gaps}


def analyze(data, writer=None):
    return CareerGuidanceAgent(writer=writer).analyze(data)


def llm_payload(*recommendations):
    return json.dumps({"recommendations": list(recommendations)})


def llm_rec(competency, category="task", title=None, evidence_ids=()):
    return {
        "category": category,
        "title": title or f"Build evidence for {competency}",
        "action": f"Do one concrete exercise for {competency}.",
        "competencies": [competency],
        "gap_summary": f"Insufficient evidence for {competency}.",
        "rationale": "Grounded in the learner's recorded work.",
        "evidence_ids": list(evidence_ids),
    }


HIGH_GAP_RECS = [
    llm_rec("technical_presentation", evidence_ids=["ev-rag"]),
    llm_rec("collaboration"),
    llm_rec("feedback_assimilation", evidence_ids=["ev-api"]),
]


# --- schema -------------------------------------------------------------------


def test_example_request_is_a_valid_profile():
    data = json.loads(EXAMPLE_REQUEST.read_text(encoding="utf-8"))

    parsed = CareerGuidanceProfile.model_validate(data)

    assert parsed.target_role == "AI Engineer"
    assert {e.evidence_id for e in parsed.evidence} >= {"ev-rag-project"}


def test_category_enum_has_exactly_three_values():
    assert [c.value for c in RecommendationCategory] == ["course", "task", "project"]
    assert ALLOWED_CATEGORIES == ["course", "task", "project"]


@pytest.mark.parametrize("category", ["course", "task", "project"])
def test_recommendation_accepts_each_allowed_category(category):
    rec = Recommendation.model_validate(llm_rec("python", category=category))

    assert rec.category is RecommendationCategory(category)


@pytest.mark.parametrize(
    "category",
    [
        "certification",
        "workshop",
        "internship",
        "book",
        "video",
        "mentorship",
        "Course",
        "",
        None,
    ],
)
def test_recommendation_rejects_any_other_category(category):
    with pytest.raises(ValidationError):
        Recommendation.model_validate(llm_rec("python", category=category))


@pytest.mark.parametrize(
    "change",
    [
        {"title": None},
        {"title": "   "},
        {"competencies": []},
        {"rationale": ""},
        {"unexpected": "field"},
    ],
)
def test_malformed_recommendation_is_rejected(change):
    data = {**llm_rec("python"), **change}
    if change.get("title") is None and "title" in change:
        data.pop("title")

    with pytest.raises(ValidationError):
        Recommendation.model_validate(data)


@pytest.mark.parametrize(
    "change",
    [
        {"target_role": ""},
        {"skills": [{"name": "Python", "level": "wizard"}]},
        {"evidence": [item("dup"), item("dup")]},
        {"evidence": [item("x", source="podcast")]},
        {"unknown_field": True},
    ],
)
def test_invalid_profiles_are_rejected(change):
    with pytest.raises(ValidationError):
        CareerGuidanceProfile.model_validate({"target_role": "AI Engineer", **change})


def test_skill_gap_cannot_be_marked_demonstrated():
    with pytest.raises(ValidationError):
        SkillGap(
            competency_key="python",
            label="Python",
            kind=CompetencyKind.TECHNICAL,
            status=EvidenceStatus.DEMONSTRATED,
            priority=GapPriority.LOW,
            gap_statement="x",
            evidence_basis="y",
        )


def test_result_rejects_recommendations_for_non_gaps_and_duplicates():
    result = analyze(technically_strong())
    base = result.model_dump()

    stray = {**base, "recommendations": [llm_rec("python")]}
    with pytest.raises(ValidationError, match="not identified gaps"):
        CareerGuidanceResult.model_validate(stray)

    repeated = {
        **base,
        "recommendations": [llm_rec("collaboration"), llm_rec("collaboration")],
    }
    with pytest.raises(ValidationError, match="Duplicate"):
        CareerGuidanceResult.model_validate(repeated)


# --- gap analysis ---------------------------------------------------------------


def test_technical_gap_detected():
    result = analyze(profile(evidence=[item("a", ["python"]), item("b", ["python"])]))

    assert status_of(result, "python") is EvidenceStatus.DEMONSTRATED
    assert status_of(result, "apis") is EvidenceStatus.INSUFFICIENT
    assert "apis" in gap_keys(result)


def test_non_technical_gap_detected():
    result = analyze(technically_strong())

    assert NON_TECHNICAL_KEYS <= gap_keys(result)


def test_mixed_technical_and_non_technical_gaps():
    result = analyze(
        profile(
            evidence=[
                item("a", ["python", "collaboration"]),
                item("b", ["python", "collaboration"]),
            ]
        )
    )
    kinds = {gap.kind for gap in result.gaps}

    assert kinds == {CompetencyKind.TECHNICAL, CompetencyKind.NON_TECHNICAL}
    assert {"python", "collaboration"}.isdisjoint(gap_keys(result))


def test_two_direct_items_demonstrate_a_competency():
    result = analyze(profile(evidence=[item("a", ["apis"]), item("b", ["rest api"])]))

    assert status_of(result, "apis") is EvidenceStatus.DEMONSTRATED
    assert "apis" not in gap_keys(result)


def test_level_backed_by_evidence_demonstrates_a_competency():
    result = analyze(
        profile(
            skills=[{"name": "pytest", "level": "advanced", "evidence_ids": ["t1"]}],
            evidence=[item("t1", ["testing"])],
        )
    )

    assert status_of(result, "testing") is EvidenceStatus.DEMONSTRATED


@pytest.mark.parametrize(
    "data",
    [
        {"evidence": [item("a", ["sql"])]},
        {"skills": [{"name": "SQL"}]},
        {"skills": [{"name": "SQL", "level": "beginner", "evidence_ids": ["a"]}]},
        {"evidence": [item("a", ["sql"], outcome="failed")]},
        {
            "evidence": [item("a", ["sql"]), item("b", ["sql"])],
            "behavioral_signals": [
                {
                    "signal": "copied queries without checking",
                    "competency": "sql",
                    "polarity": "concern",
                }
            ],
        },
    ],
    ids=["single-item", "no-level", "below-level", "failed-outcome", "concern"],
)
def test_partial_evidence_is_partial_not_demonstrated(data):
    result = analyze(profile(**data))

    assert status_of(result, "sql") is EvidenceStatus.PARTIAL
    assert "sql" in gap_keys(result)


def test_broad_taxonomy_tag_alone_can_never_demonstrate():
    tagged = [item(f"m{i}", tags=["communication"], source="meeting") for i in range(4)]

    result = analyze(profile(evidence=tagged))

    assert status_of(result, "technical_presentation") is EvidenceStatus.PARTIAL
    assert "broadly tagged" in next(
        a.rationale
        for a in result.assessments
        if a.competency_key == "technical_presentation"
    )


def test_missing_evidence_is_insufficient_and_not_called_inability():
    result = analyze(technically_strong())
    gap = next(g for g in result.gaps if g.competency_key == "technical_presentation")

    assert gap.status is EvidenceStatus.INSUFFICIENT
    assert "Insufficient demonstrated evidence" in gap.gap_statement
    assert "not a proven lack of ability" in gap.evidence_basis


def test_free_text_mentions_are_not_treated_as_evidence():
    data = profile(
        evidence=[
            item(
                "x",
                summary="Gave a great presentation and collaborated with the team.",
            )
        ]
    )

    result = analyze(data)

    assert status_of(result, "technical_presentation") is EvidenceStatus.INSUFFICIENT
    assert status_of(result, "collaboration") is EvidenceStatus.INSUFFICIENT


def test_gaps_are_ordered_by_priority():
    result = analyze(technically_strong())
    order = [gap.priority for gap in result.gaps]

    assert order == sorted(order, key=["high", "medium", "low"].index)
    assert order[0] is GapPriority.HIGH


# --- non-technical communication case ------------------------------------------


def test_strong_technical_learner_gets_communication_gaps_and_grounded_tasks():
    result = analyze(technically_strong())
    technical = [a for a in result.assessments if a.kind is CompetencyKind.TECHNICAL]
    by_key = {key: r for r in result.recommendations for key in r.competencies}

    assert all(a.status is EvidenceStatus.DEMONSTRATED for a in technical)
    for key in NON_TECHNICAL_KEYS:
        gap = next(g for g in result.gaps if g.competency_key == key)
        assert gap.status is EvidenceStatus.INSUFFICIENT
        assert gap.priority is GapPriority.HIGH

    presentation = by_key["technical_presentation"]
    assert presentation.category is RecommendationCategory.TASK
    assert "Document Q&A RAG prototype" in presentation.action
    assert "ev-rag" in presentation.evidence_ids
    assert "no evidence of presenting technical work" in presentation.rationale


# --- limited and empty profiles ------------------------------------------------


def test_empty_profile_gets_baseline_tasks_without_invented_evidence():
    writer = Mock()

    result = analyze({"target_role": "AI Engineer"}, writer=writer)

    assert result.profile_completeness is ProfileCompleteness.EMPTY
    assert all(g.status is EvidenceStatus.INSUFFICIENT for g in result.gaps)
    assert len(result.gaps) == len(AI_ENGINEER.competencies)
    assert [r.title for r in result.recommendations] == [
        "Establish a technical evidence baseline",
        "Establish a teamwork and communication evidence baseline",
    ]
    assert all(r.evidence_ids == [] for r in result.recommendations)
    assert "not proven weaknesses" in result.warnings[0]
    writer.write.assert_not_called()


def test_behavioral_evidence_with_little_technical_evidence():
    result = analyze(
        profile(
            behavioral_signals=[
                {"signal": "led the retro", "competency": "retrospective"},
                {"signal": "paired daily", "competency": "collaboration"},
            ]
        )
    )

    assert result.profile_completeness is ProfileCompleteness.LIMITED
    assert status_of(result, "collaboration") is EvidenceStatus.PARTIAL
    assert status_of(result, "python") is EvidenceStatus.INSUFFICIENT
    assert any("limited evidence" in warning for warning in result.warnings)


def test_strong_learner_has_no_gaps_and_no_recommendations():
    keys = [
        "data analysis",
        "experimentation",
        "ai product literacy",
        "sql",
        "stakeholder communication",
        "presentation",
        "collaboration",
        "prioritization",
        "feedback",
        "documentation",
        "retrospective",
    ]
    evidence = [item(f"{i}-{k}", [k]) for i in (1, 2) for k in keys]

    result = analyze({"target_role": "Product Manager", "evidence": evidence})

    assert result.gaps == []
    assert result.recommendations == []
    assert "no major gaps" in result.warnings[0]


def test_unknown_role_raises_a_controlled_error():
    with pytest.raises(UnknownRoleError, match="Supported roles"):
        analyze({"target_role": "Astronaut"})


@pytest.mark.parametrize(
    ("name", "role_id"),
    [("ML Engineer", "ai_engineer"), ("product management", "product_manager")],
)
def test_role_aliases_resolve(name, role_id):
    assert DEFAULT_ROLE_REGISTRY.resolve(name).role_id == role_id


def test_role_registry_only_accepts_the_shared_taxonomy_tags():
    bad = AI_ENGINEER.model_copy(deep=True)
    bad.competencies[0].taxonomy_tags = ["made_up_tag"]

    with pytest.raises(ValueError, match="shared taxonomy"):
        RoleRegistry([bad])


# --- recommendation quality -----------------------------------------------------


@pytest.mark.parametrize(
    "data",
    [technically_strong(), profile(evidence=[item("a", ["python"])])],
    ids=["strong", "limited"],
)
def test_recommendations_are_grounded_unique_and_capped(data):
    result = analyze(data)
    known = data.known_evidence_ids()
    identities = [(r.category, r.title.lower()) for r in result.recommendations]

    assert result.recommendations
    assert len(result.recommendations) <= MAX_RECOMMENDATIONS
    assert len(identities) == len(set(identities))
    for rec in result.recommendations:
        assert set(rec.competencies) <= gap_keys(result)
        assert set(rec.evidence_ids) <= known
        assert rec.rationale and rec.gap_summary
        assert rec.category in set(RecommendationCategory)


def test_several_technical_task_gaps_are_consolidated_into_one_project():
    result = analyze(profile(evidence=[item("a", ["python"]), item("b", ["python"])]))
    projects = [
        r
        for r in result.recommendations
        if r.category is RecommendationCategory.PROJECT
    ]

    assert len(projects) == 1
    assert len(projects[0].competencies) == 3
    for key in projects[0].competencies:
        assert next(g for g in result.gaps if g.competency_key == key).kind is (
            CompetencyKind.TECHNICAL
        )


def test_technical_gaps_without_any_technical_evidence_start_with_courses():
    result = analyze(
        profile(behavioral_signals=[{"signal": "paired", "competency": "teamwork"}])
    )
    technical = [
        r
        for r in result.recommendations
        if {g.kind for g in result.gaps if g.competency_key in r.competencies}
        == {CompetencyKind.TECHNICAL}
    ]

    assert technical
    assert all(r.category is RecommendationCategory.COURSE for r in technical)


def _assessment(required, observed, kind=CompetencyKind.TECHNICAL, status="partial"):
    status = (
        EvidenceStatus.PARTIAL if status == "partial" else EvidenceStatus.INSUFFICIENT
    )
    assessment = CompetencyAssessment(
        competency_key="python",
        label="Python",
        kind=kind,
        importance=Importance.CRITICAL,
        required_level=required,
        observed_level=observed,
        status=status,
        rationale="x",
    )
    gap = SkillGap(
        competency_key="python",
        label="Python",
        kind=kind,
        status=status,
        priority=GapPriority.MEDIUM,
        gap_statement="x",
        evidence_basis="y",
    )
    return gap, assessment


@pytest.mark.parametrize(
    ("args", "demonstrated_technical", "expected"),
    [
        ((ProficiencyLevel.ADVANCED, ProficiencyLevel.BEGINNER), True, "course"),
        ((ProficiencyLevel.INTERMEDIATE, ProficiencyLevel.BEGINNER), True, "task"),
        (
            (ProficiencyLevel.INTERMEDIATE, None, CompetencyKind.NON_TECHNICAL),
            True,
            "task",
        ),
        (
            (ProficiencyLevel.INTERMEDIATE, None, CompetencyKind.TECHNICAL, "none"),
            True,
            "task",
        ),
        (
            (ProficiencyLevel.INTERMEDIATE, None, CompetencyKind.TECHNICAL, "none"),
            False,
            "course",
        ),
    ],
)
def test_category_policy(args, demonstrated_technical, expected):
    gap, assessment = _assessment(*args)

    assert choose_category(gap, assessment, demonstrated_technical).value == expected


# --- prompt construction --------------------------------------------------------


def test_prompt_contains_role_evidence_gaps_and_category_constraint():
    data = technically_strong()
    result = analyze(data)
    assessments = assess_competencies(data, AI_ENGINEER)

    prompt = json.loads(
        build_recommendation_prompt(
            data, AI_ENGINEER, assessments, result.gaps, result.recommendations
        )
    )

    assert prompt["target_role"] == "AI Engineer"
    assert prompt["allowed_categories"] == ["course", "task", "project"]
    assert {e["evidence_id"] for e in prompt["evidence"]} == data.known_evidence_ids()
    assert {g["competency_key"] for g in prompt["identified_gaps"]} == gap_keys(result)
    assert "course, task, project" in SYSTEM_PROMPT
    assert "certification" in SYSTEM_PROMPT
    assert "Missing evidence is not proof of inability" in SYSTEM_PROMPT


# --- LLM handling ----------------------------------------------------------------


def test_valid_llm_response_is_validated_and_used():
    writer = Mock()
    writer.write.return_value = llm_payload(*HIGH_GAP_RECS)

    result = analyze(technically_strong(), writer=writer)

    assert result.generation_mode is GenerationMode.LLM
    assert {r.title for r in result.recommendations} == {
        rec["title"] for rec in HIGH_GAP_RECS
    }
    system_prompt, user_prompt = writer.write.call_args.args
    assert system_prompt == SYSTEM_PROMPT
    assert "technical_presentation" in user_prompt


def test_llm_json_inside_a_code_fence_is_accepted():
    writer = Mock()
    writer.write.return_value = f"```json\n{llm_payload(*HIGH_GAP_RECS)}\n```"

    assert analyze(technically_strong(), writer=writer).generation_mode is (
        GenerationMode.LLM
    )


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("{not json", "invalid_json"),
        ("", "empty_response"),
        (None, "empty_response"),
        ('{"items": []}', "unexpected_structure"),
        (
            llm_payload({"category": "task", "title": "Only a title"}),
            "schema_validation",
        ),
        (
            llm_payload(llm_rec("collaboration", category="certification")),
            "invalid_category",
        ),
        (llm_payload(), "empty_recommendations"),
        (llm_payload(llm_rec("python")), "ungrounded_competency"),
        (
            llm_payload(llm_rec("collaboration", evidence_ids=["ev-invented"])),
            "unknown_evidence",
        ),
    ],
)
def test_malformed_llm_output_falls_back_safely(raw, reason):
    writer = Mock()
    writer.write.return_value = raw
    deterministic = analyze(technically_strong())

    result = analyze(technically_strong(), writer=writer)

    assert result.generation_mode is GenerationMode.DETERMINISTIC_FALLBACK
    assert result.recommendations == deterministic.recommendations
    assert f"({reason})" in result.warnings[-1]
    assert writer.write.call_count == 2


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("{not json", "invalid_json"),
        (llm_payload(llm_rec("x", category="workshop")), "invalid_category"),
        ("   ", "empty_response"),
    ],
)
def test_parse_recommendation_payload_reports_reason_codes(raw, reason):
    with pytest.raises(RecommendationOutputError) as error:
        parse_recommendation_payload(raw)

    assert error.value.reason == reason


def test_writer_exception_is_contained_and_never_leaks_its_message():
    writer = Mock()
    writer.write.side_effect = RuntimeError("provider said secret-key-123")

    result = analyze(technically_strong(), writer=writer)

    assert result.generation_mode is GenerationMode.DETERMINISTIC_FALLBACK
    assert "model_request_failed" in result.warnings[-1]
    assert "secret-key-123" not in json.dumps(result.model_dump(mode="json"))


def test_llm_retry_succeeds_on_the_second_attempt():
    writer = Mock()
    writer.write.side_effect = ["{broken", llm_payload(*HIGH_GAP_RECS)]

    result = analyze(technically_strong(), writer=writer)

    assert result.generation_mode is GenerationMode.LLM
    assert writer.write.call_count == 2


def test_high_priority_gaps_skipped_by_the_llm_are_backfilled():
    writer = Mock()
    writer.write.return_value = llm_payload(llm_rec("documentation"))

    result = analyze(technically_strong(), writer=writer)
    covered = {key for r in result.recommendations for key in r.competencies}

    assert result.generation_mode is GenerationMode.LLM
    assert NON_TECHNICAL_KEYS <= covered
    assert "model skipped" in result.warnings[-1]


def test_llm_writer_uses_the_shared_chat_client_contract():
    completion = Mock(return_value="{}")

    LLMRecommendationWriter("test-model", completion).write("system", "user")

    kwargs = completion.call_args.kwargs
    assert kwargs["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
    assert kwargs["model_name"] == "test-model"
    assert kwargs["temperature"] == 0


def test_llm_writer_requires_configuration(monkeypatch):
    for name in ("LITE_LLM_KEY", "LITELLM_BASE_URL", "PRIMARY_MODEL", "AI_MODEL"):
        monkeypatch.setattr(f"{AGENT_MODULE}.{name}", None)

    with pytest.raises(CareerGuidanceError, match="Configure"):
        LLMRecommendationWriter.from_env()


# --- CLI ------------------------------------------------------------------------


def test_cli_prints_a_valid_result_for_the_example(capsys):
    assert main([str(EXAMPLE_REQUEST)]) == 0

    result = CareerGuidanceResult.model_validate_json(capsys.readouterr().out)
    assert result.role_id == "ai_engineer"
    assert result.generation_mode is GenerationMode.DETERMINISTIC


def test_cli_reports_errors_without_a_traceback(tmp_path, capsys):
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"target_role": "Astronaut"}), encoding="utf-8")

    assert main([str(request)]) == 2
    assert "Supported roles" in capsys.readouterr().err
