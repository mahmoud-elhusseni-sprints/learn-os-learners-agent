"""Career Guidance Agent: evidence-first skill gaps and recommendations.

Flow::

    profile -> resolve role -> assess competencies -> identify gaps
            -> deterministic recommendations
            -> (optional) LLM rewording, validated and grounded
            -> CareerGuidanceResult (validated again)

Gap detection is always deterministic. The LLM, when injected, only words the
recommendations; malformed or ungrounded output is rejected and the
deterministic recommendations are used instead, with a warning in the result.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from src.app.core.config import AI_MODEL, LITE_LLM_KEY, LITELLM_BASE_URL, PRIMARY_MODEL
from src.app.core.llm_client import generate_chat_completion
from src.app.schemas.career_guidance import (
    CareerGuidanceProfile,
    CareerGuidanceResult,
    CompetencyAssessment,
    GenerationMode,
    ProfileCompleteness,
    Recommendation,
    RoleDefinition,
    SkillGap,
)

from .gap_analysis import assess_competencies, identify_gaps, profile_completeness
from .prompts import SYSTEM_PROMPT, build_recommendation_prompt
from .recommendations import (
    MAX_RECOMMENDATIONS,
    RecommendationOutputError,
    build_deterministic_recommendations,
    dedupe,
    ensure_high_priority_coverage,
    parse_recommendation_payload,
    sort_by_priority,
    validate_grounding,
)
from .roles import DEFAULT_ROLE_REGISTRY, RoleRegistry


class CareerGuidanceError(RuntimeError):
    """The request could not be analysed (for example an unsupported role)."""


class UnknownRoleError(CareerGuidanceError):
    """The target role has no competency framework."""


class RecommendationWriter(Protocol):
    """Replaceable LLM boundary: prompts in, raw model text out."""

    def write(self, system_prompt: str, user_prompt: str) -> str: ...


class LLMRecommendationWriter:
    """Recommendation writer backed by the shared LiteLLM chat client."""

    def __init__(
        self,
        model_name: str | None = None,
        completion: Callable[..., str] | None = None,
    ) -> None:
        self.model_name = model_name
        self.completion = completion or generate_chat_completion

    @classmethod
    def from_env(cls) -> LLMRecommendationWriter:
        model = PRIMARY_MODEL or AI_MODEL
        if not all((LITE_LLM_KEY, LITELLM_BASE_URL, model)):
            raise CareerGuidanceError(
                "Configure AI_AGENT_URL, AI_API_KEY and PRIMARY_MODEL."
            )
        return cls(model)

    def write(self, system_prompt: str, user_prompt: str) -> str:
        return self.completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model_name=self.model_name,
            temperature=0,
        )


class CareerGuidanceAgent:
    """Analyse one learner against one target role."""

    def __init__(
        self,
        writer: RecommendationWriter | None = None,
        roles: RoleRegistry = DEFAULT_ROLE_REGISTRY,
        max_attempts: int = 2,
    ) -> None:
        self.writer = writer
        self.roles = roles
        self.max_attempts = max(1, max_attempts)

    def analyze(
        self, profile: CareerGuidanceProfile | dict[str, Any]
    ) -> CareerGuidanceResult:
        """Return validated gaps and recommendations, never partial output."""
        if not isinstance(profile, CareerGuidanceProfile):
            profile = CareerGuidanceProfile.model_validate(profile)

        role = self.roles.resolve(profile.target_role)
        if role is None:
            raise UnknownRoleError(
                f"No competency framework for '{profile.target_role}'. "
                f"Supported roles: {', '.join(self.roles.titles)}."
            )

        completeness = profile_completeness(profile)
        assessments = assess_competencies(profile, role)
        gaps = identify_gaps(assessments, role.title)
        fallback = build_deterministic_recommendations(
            profile, role, assessments, gaps, completeness
        )
        recommendations, mode, warnings = self._recommend(
            profile, role, assessments, gaps, fallback, completeness
        )

        return CareerGuidanceResult(
            learner_id=profile.learner_id,
            target_role=profile.target_role,
            role_id=role.role_id,
            role_title=role.title,
            profile_completeness=completeness,
            assessments=assessments,
            gaps=gaps,
            recommendations=recommendations,
            generation_mode=mode,
            warnings=warnings,
        )

    def _recommend(
        self,
        profile: CareerGuidanceProfile,
        role: RoleDefinition,
        assessments: list[CompetencyAssessment],
        gaps: list[SkillGap],
        fallback: list[Recommendation],
        completeness: ProfileCompleteness,
    ) -> tuple[list[Recommendation], GenerationMode, list[str]]:
        warnings: list[str] = []
        if completeness is ProfileCompleteness.EMPTY:
            warnings.append(
                "The profile contains no evidence. Gaps reflect missing evidence, "
                "not proven weaknesses; recommendations focus on building a "
                "baseline."
            )
            return fallback, GenerationMode.DETERMINISTIC, warnings
        if not gaps:
            warnings.append(
                "Every competency for this role is demonstrated by the evidence; "
                "no major gaps were found."
            )
            return [], GenerationMode.DETERMINISTIC, warnings
        if completeness is ProfileCompleteness.LIMITED:
            warnings.append(
                "The profile has limited evidence, so several gaps may reflect "
                "missing records rather than missing ability."
            )
        if self.writer is None:
            return fallback, GenerationMode.DETERMINISTIC, warnings

        prompt = build_recommendation_prompt(profile, role, assessments, gaps, fallback)
        known_ids = profile.known_evidence_ids()
        reason = "unknown"
        for _ in range(self.max_attempts):
            try:
                raw = self.writer.write(SYSTEM_PROMPT, prompt)
                written = parse_recommendation_payload(raw)
                written = validate_grounding(written, gaps, known_ids)
                merged, uncovered = ensure_high_priority_coverage(
                    dedupe(written), fallback, gaps
                )
                if uncovered:
                    warnings.append(
                        "Deterministic recommendations were added for "
                        f"high-priority gaps the model skipped: {', '.join(uncovered)}."
                    )
                ordered = sort_by_priority(merged, gaps)[:MAX_RECOMMENDATIONS]
                return ordered, GenerationMode.LLM, warnings
            except RecommendationOutputError as error:
                reason = error.reason
            except Exception:
                reason = "model_request_failed"

        warnings.append(
            f"Model output was rejected ({reason}) after {self.max_attempts} "
            "attempt(s); deterministic recommendations were used instead."
        )
        return fallback, GenerationMode.DETERMINISTIC_FALLBACK, warnings
