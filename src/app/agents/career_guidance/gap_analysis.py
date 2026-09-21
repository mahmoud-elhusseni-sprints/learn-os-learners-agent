"""Deterministic gap analysis: target-role expectations vs learner evidence.

No LLM is involved here. Each role competency is matched against structured
profile data - evidence items that name the competency, skill entries, and
behavioral signals - never by scanning free text. The result is one of three
statuses:

* ``demonstrated`` - at least two successful direct evidence items, or a
  skill at or above the required level backed by cited evidence, and no
  concern signals;
* ``partially_demonstrated`` - some related evidence exists, but it is thin,
  below the required level, unsuccessful, only broadly tagged, or contradicted
  by a concern signal;
* ``insufficient_evidence`` - nothing in the profile relates to it. This is
  explicitly *not* a claim that the learner lacks the skill.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.app.schemas.career_guidance import (
    CareerGuidanceProfile,
    CompetencyAssessment,
    CompetencyRequirement,
    EvidenceStatus,
    GapPriority,
    Importance,
    ProficiencyLevel,
    ProfileCompleteness,
    RoleDefinition,
    SignalPolarity,
    SkillGap,
)

from .roles import normalize

FAILED_OUTCOMES = frozenset(
    normalize(value)
    for value in ("failed", "fail", "not passed", "rejected", "retry", "incomplete")
)
LIMITED_EVIDENCE_THRESHOLD = 3
PRIORITY_ORDER = {GapPriority.HIGH: 0, GapPriority.MEDIUM: 1, GapPriority.LOW: 2}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def label_phrase(label: str) -> str:
    """'Data analysis' -> 'data analysis', but keep acronyms like 'SQL'."""
    return label if label.split()[0].isupper() else label[0].lower() + label[1:]


def with_article(noun: str) -> str:
    """'AI Engineer' -> 'an AI Engineer', 'Product Manager' -> 'a Product Manager'."""
    return f"{'an' if noun[:1].upper() in 'AEIOU' else 'a'} {noun}"


@dataclass
class _Findings:
    """Everything in the profile that relates to one competency."""

    direct: list[str] = field(default_factory=list)
    unsuccessful: list[str] = field(default_factory=list)
    tag_only: list[str] = field(default_factory=list)
    skill_names: list[str] = field(default_factory=list)
    skill_evidence: list[str] = field(default_factory=list)
    positive_signals: list[str] = field(default_factory=list)
    signal_evidence: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    concern_evidence: list[str] = field(default_factory=list)
    observed_level: ProficiencyLevel | None = None

    @property
    def found_anything(self) -> bool:
        return bool(
            self.direct
            or self.unsuccessful
            or self.tag_only
            or self.skill_names
            or self.positive_signals
            or self.concerns
        )


def competency_terms(requirement: CompetencyRequirement) -> set[str]:
    """Normalized names that refer to this competency."""
    names = [requirement.key.replace("_", " "), requirement.label]
    return {normalize(name) for name in [*names, *requirement.aliases]}


def profile_completeness(profile: CareerGuidanceProfile) -> ProfileCompleteness:
    if not (profile.evidence or profile.skills or profile.behavioral_signals):
        return ProfileCompleteness.EMPTY
    if len(profile.evidence) < LIMITED_EVIDENCE_THRESHOLD:
        return ProfileCompleteness.LIMITED
    return ProfileCompleteness.SUBSTANTIAL


def _collect(
    profile: CareerGuidanceProfile, requirement: CompetencyRequirement
) -> _Findings:
    terms = competency_terms(requirement)
    findings = _Findings()

    for item in profile.evidence:
        if any(normalize(name) in terms for name in item.competencies):
            failed = item.outcome is not None and normalize(item.outcome) in (
                FAILED_OUTCOMES
            )
            target = findings.unsuccessful if failed else findings.direct
            target.append(item.evidence_id)
        elif not item.competencies and set(item.tags) & set(requirement.taxonomy_tags):
            findings.tag_only.append(item.evidence_id)

    for skill in profile.skills:
        if normalize(skill.name) not in terms:
            continue
        findings.skill_names.append(skill.name)
        findings.skill_evidence.extend(skill.evidence_ids)
        if skill.level is not None and (
            findings.observed_level is None
            or skill.level.rank > findings.observed_level.rank
        ):
            findings.observed_level = skill.level

    for signal in profile.behavioral_signals:
        if normalize(signal.competency or signal.signal) not in terms:
            continue
        if signal.polarity is SignalPolarity.CONCERN:
            findings.concerns.append(signal.signal)
            findings.concern_evidence.extend(signal.evidence_ids)
        else:
            findings.positive_signals.append(signal.signal)
            findings.signal_evidence.extend(signal.evidence_ids)
    return findings


def _decide(
    findings: _Findings, requirement: CompetencyRequirement
) -> tuple[EvidenceStatus, str]:
    """Pick the status and the most important reason behind it."""
    if not findings.found_anything:
        return EvidenceStatus.INSUFFICIENT, ""

    supporting = _unique(findings.direct + findings.skill_evidence)
    level = findings.observed_level
    below_level = level is not None and level.rank < requirement.required_level.rank
    enough = len(_unique(findings.direct)) >= 2 or (
        bool(supporting) and level is not None
    )

    if enough and not below_level and not findings.concerns:
        return EvidenceStatus.DEMONSTRATED, ""
    if below_level:
        reason = (
            f"the highest recorded level ({level}) is below the "
            f"{requirement.required_level} level the role expects"
        )
    elif findings.concerns and not supporting:
        reason = (
            "no evidence shows this competency working well, and a concern was "
            "observed"
        )
    elif findings.concerns:
        reason = "concern signals contradict the supporting evidence"
    elif findings.unsuccessful and not findings.direct:
        reason = "the related attempts did not have a successful outcome"
    elif not supporting:
        reason = (
            "the related evidence is indirect (broad tags or behavioral signals) "
            "rather than a reviewed item naming this competency"
        )
    else:
        reason = "there is not yet enough independent evidence to confirm it"
    return EvidenceStatus.PARTIAL, reason


def _describe(findings: _Findings) -> list[str]:
    parts: list[str] = []
    if findings.direct:
        ids = ", ".join(_unique(findings.direct))
        parts.append(f"{len(_unique(findings.direct))} direct evidence item(s) ({ids})")
    if findings.unsuccessful:
        ids = ", ".join(_unique(findings.unsuccessful))
        parts.append(f"unsuccessful attempt(s) ({ids})")
    if findings.skill_names:
        text = f"skill entry '{', '.join(_unique(findings.skill_names))}'"
        if findings.observed_level:
            text += f" at {findings.observed_level} level"
        if findings.skill_evidence:
            text += f" citing {', '.join(_unique(findings.skill_evidence))}"
        else:
            text += " with no cited evidence"
        parts.append(text)
    if findings.tag_only:
        ids = ", ".join(_unique(findings.tag_only))
        parts.append(f"broadly tagged item(s) ({ids})")
    if findings.positive_signals:
        parts.append(
            f"positive signal(s): {', '.join(_unique(findings.positive_signals))}"
        )
    if findings.concerns:
        parts.append(f"concern signal(s): {', '.join(_unique(findings.concerns))}")
    return parts


def assess_competency(
    profile: CareerGuidanceProfile, requirement: CompetencyRequirement
) -> CompetencyAssessment:
    findings = _collect(profile, requirement)
    status, reason = _decide(findings, requirement)

    if status is EvidenceStatus.INSUFFICIENT:
        rationale = (
            f"Insufficient evidence: nothing in the profile relates to "
            f"{requirement.label}. This reflects missing evidence, not a proven "
            "lack of ability."
        )
    else:
        found = "; ".join(_describe(findings))
        if status is EvidenceStatus.DEMONSTRATED:
            rationale = f"Demonstrated by {found}."
        else:
            rationale = (
                f"Partially demonstrated. Related evidence: {found}. "
                f"However, {reason}."
            )

    supporting = _unique(
        findings.direct
        + findings.skill_evidence
        + findings.signal_evidence
        + findings.unsuccessful
        + findings.tag_only
    )
    return CompetencyAssessment(
        competency_key=requirement.key,
        label=requirement.label,
        kind=requirement.kind,
        importance=requirement.importance,
        required_level=requirement.required_level,
        status=status,
        observed_level=findings.observed_level,
        supporting_evidence_ids=supporting,
        concern_evidence_ids=_unique(findings.concern_evidence),
        rationale=rationale,
    )


def assess_competencies(
    profile: CareerGuidanceProfile, role: RoleDefinition
) -> list[CompetencyAssessment]:
    """One assessment per role competency, in the role's order."""
    return [
        assess_competency(profile, requirement) for requirement in role.competencies
    ]


def _priority(assessment: CompetencyAssessment) -> GapPriority:
    critical = assessment.importance is Importance.CRITICAL
    if assessment.status is EvidenceStatus.INSUFFICIENT:
        return GapPriority.HIGH if critical else GapPriority.MEDIUM
    return GapPriority.MEDIUM if critical else GapPriority.LOW


def _gap_statement(assessment: CompetencyAssessment, role_title: str) -> str:
    if assessment.status is EvidenceStatus.INSUFFICIENT:
        return (
            f"Insufficient demonstrated evidence for {label_phrase(assessment.label)}, "
            f"which {with_article(role_title)} is expected to show at "
            f"{assessment.required_level} level."
        )
    return (
        f"{assessment.label} is only partially demonstrated against the "
        f"{assessment.required_level} level expected of {with_article(role_title)}."
    )


def identify_gaps(
    assessments: list[CompetencyAssessment], role_title: str
) -> list[SkillGap]:
    """Every non-demonstrated competency as a gap, highest priority first."""
    gaps = [
        SkillGap(
            competency_key=assessment.competency_key,
            label=assessment.label,
            kind=assessment.kind,
            status=assessment.status,
            priority=_priority(assessment),
            gap_statement=_gap_statement(assessment, role_title),
            evidence_basis=assessment.rationale,
            related_evidence_ids=_unique(
                assessment.supporting_evidence_ids + assessment.concern_evidence_ids
            ),
        )
        for assessment in assessments
        if assessment.status is not EvidenceStatus.DEMONSTRATED
    ]
    return sorted(gaps, key=lambda gap: PRIORITY_ORDER[gap.priority])
