"""Recommendation engine for the Career Guidance Agent.

Two responsibilities, kept separate:

1. ``build_deterministic_recommendations`` turns gaps into grounded
   recommendations using an explicit category policy. It is the baseline
   when no LLM is configured and the safe fallback when an LLM misbehaves.
2. ``parse_recommendation_payload`` / ``validate_grounding`` check raw LLM
   text: valid JSON, the ``RecommendationSet`` schema (which restricts the
   category to course/task/project), and that every recommendation targets a
   real gap and cites only evidence that exists in the profile.

Category policy:

* non-technical gap -> ``task`` (a focused, observable exercise);
* technical gap two or more levels below the requirement -> ``course``;
* other partial technical gap -> ``task``;
* technical gap with no evidence -> ``task`` when the learner already
  demonstrates other technical skills, otherwise ``course``;
* two or more technical ``task`` gaps -> consolidated into one ``project``.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from src.app.schemas.career_guidance import (
    CareerGuidanceProfile,
    CompetencyAssessment,
    CompetencyKind,
    CompetencyRequirement,
    EvidenceItem,
    EvidenceSource,
    EvidenceStatus,
    GapPriority,
    ProfileCompleteness,
    Recommendation,
    RecommendationCategory,
    RecommendationSet,
    RoleDefinition,
    SkillGap,
    normalize_title,
)

from .gap_analysis import FAILED_OUTCOMES, PRIORITY_ORDER, label_phrase, with_article
from .roles import normalize

MAX_RECOMMENDATIONS = 6
MAX_PROJECT_COMPETENCIES = 3
COURSE_LEVEL_GAP = 2
BASELINE_COMPETENCIES = 3
ANCHOR_SOURCES = (
    EvidenceSource.PROJECT,
    EvidenceSource.REVIEW,
    EvidenceSource.ASSESSMENT,
    EvidenceSource.TASK,
)
NO_ANCHOR = "a piece of work you have already completed"


class RecommendationOutputError(ValueError):
    """LLM output was rejected; ``reason`` is a short machine-readable code."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


# --- deterministic engine ---------------------------------------------------


def select_anchor(
    profile: CareerGuidanceProfile, assessments: list[CompetencyAssessment]
) -> EvidenceItem | None:
    """The learner's strongest successful piece of work to build tasks on."""
    items = {item.evidence_id: item for item in profile.evidence}

    def usable(item: EvidenceItem | None) -> bool:
        return (
            item is not None
            and item.source_type in ANCHOR_SOURCES
            and (item.outcome is None or normalize(item.outcome) not in FAILED_OUTCOMES)
        )

    for assessment in assessments:
        if assessment.status is not EvidenceStatus.DEMONSTRATED:
            continue
        for evidence_id in assessment.supporting_evidence_ids:
            item = items.get(evidence_id)
            if usable(item):
                return item
    return next((item for item in profile.evidence if usable(item)), None)


def choose_category(
    gap: SkillGap,
    assessment: CompetencyAssessment,
    has_demonstrated_technical: bool,
) -> RecommendationCategory:
    if gap.kind is CompetencyKind.NON_TECHNICAL:
        return RecommendationCategory.TASK
    if gap.status is EvidenceStatus.PARTIAL:
        observed = assessment.observed_level
        if observed and assessment.required_level.rank - observed.rank >= (
            COURSE_LEVEL_GAP
        ):
            return RecommendationCategory.COURSE
        return RecommendationCategory.TASK
    if has_demonstrated_technical:
        return RecommendationCategory.TASK
    return RecommendationCategory.COURSE


def _fill(template: str, anchor: EvidenceItem | None) -> str:
    return template.replace("{anchor}", f"'{anchor.title}'" if anchor else NO_ANCHOR)


def _single_rationale(
    gap: SkillGap, category: RecommendationCategory, anchor: EvidenceItem | None
) -> str:
    if gap.status is EvidenceStatus.PARTIAL:
        return (
            f"{gap.evidence_basis} This {category.value} targets that shortfall "
            "and produces new evidence that can be reviewed."
        )
    if gap.kind is CompetencyKind.NON_TECHNICAL and anchor:
        return (
            f"The profile shows completed work such as '{anchor.title}' "
            f"({anchor.evidence_id}) but no evidence of {label_phrase(gap.label)}. "
            "Missing evidence is not proof of inability; this task creates that "
            "evidence by building on work already done."
        )
    return (
        f"No evidence in the profile relates to {label_phrase(gap.label)}. This is a "
        f"missing-evidence gap rather than a proven weakness, so the "
        f"{category.value} establishes a verifiable baseline."
    )


def _single(
    gap: SkillGap,
    requirement: CompetencyRequirement,
    category: RecommendationCategory,
    anchor: EvidenceItem | None,
) -> Recommendation:
    template = (
        requirement.course
        if category is RecommendationCategory.COURSE
        else requirement.task
    )
    uses_anchor = "{anchor}" in template.action and anchor is not None
    evidence = gap.related_evidence_ids + (
        [anchor.evidence_id] if uses_anchor and anchor else []
    )
    return Recommendation(
        category=category,
        title=template.title,
        action=_fill(template.action, anchor),
        competencies=[gap.competency_key],
        gap_summary=gap.gap_statement,
        rationale=_single_rationale(gap, category, anchor),
        evidence_ids=_unique(evidence),
    )


def _project(role: RoleDefinition, gaps: list[SkillGap]) -> Recommendation:
    labels = ", ".join(label_phrase(gap.label) for gap in gaps)
    evidence: list[str] = []
    for gap in gaps:
        evidence.extend(gap.related_evidence_ids)
    return Recommendation(
        category=RecommendationCategory.PROJECT,
        title=role.project.title,
        action=role.project.action.replace("{competencies}", labels),
        competencies=[gap.competency_key for gap in gaps],
        gap_summary=f"Insufficient or partial demonstrated evidence for {labels}.",
        rationale=(
            f"{len(gaps)} technical competencies ({labels}) are not yet "
            "demonstrated by the profile's evidence. One integrated project "
            "produces reviewable evidence for all of them instead of several "
            "disconnected exercises."
        ),
        evidence_ids=_unique(evidence),
    )


def baseline_recommendations(
    role: RoleDefinition, gaps: list[SkillGap]
) -> list[Recommendation]:
    """For an empty profile: gather first evidence, don't diagnose deficits."""
    recommendations: list[Recommendation] = []
    plans = (
        (
            CompetencyKind.TECHNICAL,
            "Establish a technical evidence baseline",
            "Complete one short, reviewed exercise for each of: {labels}. Keep "
            "the submissions and reviewer feedback so they can be recorded as "
            "evidence.",
        ),
        (
            CompetencyKind.NON_TECHNICAL,
            "Establish a teamwork and communication evidence baseline",
            "During your next team task, keep a short log that shows {labels}: "
            "note feedback you received, how you applied it, and one update you "
            "shared with the team.",
        ),
    )
    for kind, title, action in plans:
        chosen = [gap for gap in gaps if gap.kind is kind][:BASELINE_COMPETENCIES]
        if not chosen:
            continue
        labels = ", ".join(label_phrase(gap.label) for gap in chosen)
        recommendations.append(
            Recommendation(
                category=RecommendationCategory.TASK,
                title=title,
                action=action.replace("{labels}", labels),
                competencies=[gap.competency_key for gap in chosen],
                gap_summary=f"No demonstrated evidence is recorded yet for {labels}.",
                rationale=(
                    "The profile contains no evidence, skills or behavioral "
                    "signals, so no specific deficiency can be identified. This "
                    "task produces the first reviewable evidence for the most "
                    f"important competencies of {with_article(role.title)}."
                ),
            )
        )
    return recommendations


def dedupe(recommendations: list[Recommendation]) -> list[Recommendation]:
    """Drop repeats by (category, title) or (category, competency set)."""
    seen: set[tuple[RecommendationCategory, str]] = set()
    unique: list[Recommendation] = []
    for recommendation in recommendations:
        title_key = (recommendation.category, normalize_title(recommendation.title))
        scope_key = (
            recommendation.category,
            "|".join(sorted(recommendation.competencies)),
        )
        if title_key in seen or scope_key in seen:
            continue
        seen.update({title_key, scope_key})
        unique.append(recommendation)
    return unique


def sort_by_priority(
    recommendations: list[Recommendation], gaps: list[SkillGap]
) -> list[Recommendation]:
    rank = {gap.competency_key: PRIORITY_ORDER[gap.priority] for gap in gaps}
    return sorted(
        recommendations,
        key=lambda item: min(rank.get(key, 99) for key in item.competencies),
    )


def build_deterministic_recommendations(
    profile: CareerGuidanceProfile,
    role: RoleDefinition,
    assessments: list[CompetencyAssessment],
    gaps: list[SkillGap],
    completeness: ProfileCompleteness,
) -> list[Recommendation]:
    if not gaps:
        return []
    if completeness is ProfileCompleteness.EMPTY:
        return baseline_recommendations(role, gaps)

    requirements = {competency.key: competency for competency in role.competencies}
    by_key = {assessment.competency_key: assessment for assessment in assessments}
    has_technical = any(
        item.kind is CompetencyKind.TECHNICAL
        and item.status is EvidenceStatus.DEMONSTRATED
        for item in assessments
    )
    anchor = select_anchor(profile, assessments)
    categories = {
        gap.competency_key: choose_category(
            gap, by_key[gap.competency_key], has_technical
        )
        for gap in gaps
    }

    recommendations: list[Recommendation] = []
    technical_tasks = [
        gap
        for gap in gaps
        if gap.kind is CompetencyKind.TECHNICAL
        and categories[gap.competency_key] is RecommendationCategory.TASK
    ]
    consolidated: set[str] = set()
    if len(technical_tasks) >= 2:
        chosen = technical_tasks[:MAX_PROJECT_COMPETENCIES]
        recommendations.append(_project(role, chosen))
        consolidated = {gap.competency_key for gap in chosen}

    for gap in gaps:
        if gap.competency_key in consolidated:
            continue
        recommendations.append(
            _single(
                gap,
                requirements[gap.competency_key],
                categories[gap.competency_key],
                anchor,
            )
        )
    ordered = sort_by_priority(dedupe(recommendations), gaps)
    return ordered[:MAX_RECOMMENDATIONS]


# --- LLM output validation --------------------------------------------------


_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def parse_recommendation_payload(raw: str | None) -> list[Recommendation]:
    """Parse raw model text into validated recommendations or raise."""
    if raw is None or not raw.strip():
        raise RecommendationOutputError("empty_response")
    text = _FENCE.sub("", raw.strip())
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise RecommendationOutputError("invalid_json", str(error)) from None
    if isinstance(data, list):
        data = {"recommendations": data}
    if not isinstance(data, dict) or "recommendations" not in data:
        raise RecommendationOutputError(
            "unexpected_structure", "expected an object with 'recommendations'"
        )
    try:
        parsed = RecommendationSet.model_validate(data)
    except ValidationError as error:
        fields = {str(part) for issue in error.errors() for part in issue["loc"]}
        reason = "invalid_category" if "category" in fields else "schema_validation"
        detail = f"{error.error_count()} error(s)"
        raise RecommendationOutputError(reason, detail) from None
    if not parsed.recommendations:
        raise RecommendationOutputError("empty_recommendations")
    return parsed.recommendations


def validate_grounding(
    recommendations: list[Recommendation],
    gaps: list[SkillGap],
    known_evidence_ids: set[str],
) -> list[Recommendation]:
    """Reject recommendations that target non-gaps or invent evidence IDs."""
    gap_keys = {gap.competency_key for gap in gaps}
    for recommendation in recommendations:
        unknown = [key for key in recommendation.competencies if key not in gap_keys]
        if unknown:
            raise RecommendationOutputError("ungrounded_competency", ", ".join(unknown))
        invented = [
            evidence_id
            for evidence_id in recommendation.evidence_ids
            if evidence_id not in known_evidence_ids
        ]
        if invented:
            raise RecommendationOutputError("unknown_evidence", ", ".join(invented))
    return recommendations


def ensure_high_priority_coverage(
    recommendations: list[Recommendation],
    fallback: list[Recommendation],
    gaps: list[SkillGap],
) -> tuple[list[Recommendation], list[str]]:
    """Add deterministic recommendations for high-priority gaps the LLM skipped."""
    covered = {key for item in recommendations for key in item.competencies}
    missing = [
        gap.competency_key
        for gap in gaps
        if gap.priority is GapPriority.HIGH and gap.competency_key not in covered
    ]
    extra = [
        item for item in fallback if any(key in missing for key in item.competencies)
    ]
    return dedupe([*recommendations, *extra]), missing
