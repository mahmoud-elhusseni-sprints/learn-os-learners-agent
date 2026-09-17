"""Task 22: Career Guidance Agent - evidence-first skill gap recommendations."""

from src.app.schemas.career_guidance import (
    CareerGuidanceProfile,
    CareerGuidanceResult,
    Recommendation,
    RecommendationCategory,
)

from .agent import (
    CareerGuidanceAgent,
    CareerGuidanceError,
    LLMRecommendationWriter,
    UnknownRoleError,
)
from .roles import DEFAULT_ROLE_REGISTRY, RoleRegistry

__all__ = [
    "CareerGuidanceAgent",
    "CareerGuidanceError",
    "CareerGuidanceProfile",
    "CareerGuidanceResult",
    "DEFAULT_ROLE_REGISTRY",
    "LLMRecommendationWriter",
    "Recommendation",
    "RecommendationCategory",
    "RoleRegistry",
    "UnknownRoleError",
]
