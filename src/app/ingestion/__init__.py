"""Ingestion package for processing assessments, transcripts, and reviews."""

from src.app.core.tags import ALLOWED_TAXONOMY_TAGS
from src.app.ingestion.evidence_payload_generation import generate_datasource_nodes
from src.app.ingestion.generate_memory_cards import (
    GroupContext,
    build_card,
    format_as_memory_card_code,
    process_conversation_file,
    process_transcript_file,
)
from src.app.ingestion.learner_profile_extraction import extract_learner_profiles
from src.app.ingestion.lms_assessment_extraction import extract_lms_assessments
from src.app.ingestion.memory_card_extraction import (
    extract_memory_cards_from_assessments,
    extract_memory_cards_from_reviews,
    generate_memory_card_nodes,
    merge_memory_cards,
)
from src.app.ingestion.mentor_rubric_extraction import (
    build_attempt_map,
    build_deadline_map,
    compute_timeliness,
    extract_mentor_evaluations,
    extract_rubric_taxonomies,
    parse_feedback_raw,
)
from src.app.ingestion.pipeline import run_pipeline

__all__ = [
    "ALLOWED_TAXONOMY_TAGS",
    "GroupContext",
    "build_card",
    "format_as_memory_card_code",
    "process_conversation_file",
    "process_transcript_file",
    "extract_learner_profiles",
    "build_attempt_map",
    "build_deadline_map",
    "compute_timeliness",
    "extract_rubric_taxonomies",
    "parse_feedback_raw",
    "extract_mentor_evaluations",
    "extract_lms_assessments",
    "extract_memory_cards_from_assessments",
    "extract_memory_cards_from_reviews",
    "merge_memory_cards",
    "generate_memory_card_nodes",
    "generate_datasource_nodes",
    "run_pipeline",
]
