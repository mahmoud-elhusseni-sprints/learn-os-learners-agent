import json
import logging
import os
import uuid
from typing import Any, Dict, List, Sequence

from src.app.core import ALLOWED_TAXONOMY_SET, BEHAVIOR_METRIC_TAG_MAP
from src.app.core.config import (
    LMS_ASSESSMENTS_OUTPUT_FILE,
    MEMORY_CARDS_OUTPUT_FILE,
    RUBRICS_OUTPUT_FILE,
)
from src.app.models.models import DataSource, MemoryCard

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def canonicalize_tags(
    raw_inputs: Sequence[Any], default_fallback: str = "technical_skills"
) -> List[str]:

    matched_tags: List[str] = []

    for item in raw_inputs:
        tokens = (
            [item]
            if isinstance(item, str)
            else list(item)
            if isinstance(item, (list, tuple, set))
            else []
        )
        for tok in tokens:
            tag = str(tok).strip().lower()
            if tag in ALLOWED_TAXONOMY_SET and tag not in matched_tags:
                matched_tags.append(tag)

    if not matched_tags:
        matched_tags = [default_fallback]

    return matched_tags[:3]


def _deterministic_card_id(*parts: str) -> str:
    raw_key = ":".join(str(p) for p in parts)
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_key))


def extract_memory_cards_from_assessments(
    assessments_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    cards_by_id: Dict[str, Dict[str, Any]] = {}

    for record in assessments_data:
        learner_id = record.get("learner_id")
        mastery_cards = record.get("mastery_memory_cards", [])
        lx_id = record.get("lx_id") or "assessment"
        answers = record.get("answers", [])
        source_datasource_id = DataSource.generate_deterministic_id(
            learner_id=str(learner_id),
            lx_id=str(record.get("lx_id", "lms_assessment")),
            timestamp=(
                record.get("terminated_at")
                or record.get("activated_at")
                or "2026-08-01T00:00:00Z"
            ),
            source_type="assesments",
            attempt=1,
        )

        for raw_card in mastery_cards:
            if not isinstance(raw_card, dict):
                continue

            card_id = raw_card.get("card_id")
            if not card_id:
                continue

            raw_tags = raw_card.get("tags") or raw_card.get("profile_hints") or []
            if isinstance(raw_tags, str):
                raw_tags = [raw_tags]
            metric_key = raw_card.get("metric_key", "general_competency")

            canonical_tags = canonicalize_tags(
                raw_tags + [metric_key, raw_card.get("content", "")],
                default_fallback="technical_skills",
            )

            if card_id not in cards_by_id:
                associated_learners = []
                if learner_id:
                    associated_learners.append(learner_id)

                card_obj = MemoryCard(
                    card_id=card_id,
                    metric_key=metric_key,
                    content=raw_card.get("content", ""),
                    rationale=raw_card.get("rationale"),
                    tags=canonical_tags,
                    created_at=raw_card.get("created_at"),
                    associated_learner_ids=associated_learners,
                    source_datasource_id=source_datasource_id,
                )
                cards_by_id[card_id] = card_obj.model_dump(
                    exclude={"profile_hints", "meeting_id"}
                )
            else:
                existing_learners = cards_by_id[card_id]["associated_learner_ids"]
                if learner_id and learner_id not in existing_learners:
                    existing_learners.append(learner_id)
                cards_by_id[card_id]["tags"] = canonicalize_tags(
                    cards_by_id[card_id]["tags"] + canonical_tags
                )

        if not mastery_cards and answers:
            for ans in answers:
                if not isinstance(ans, dict):
                    continue
                q_id = ans.get("question_id", "Q")
                metric_key = (
                    ans.get("metric_key") or ans.get("domain") or "technical_skills"
                )
                score = ans.get("score")
                learner_answer = ans.get("learner_answer", "")
                notes = ans.get("evaluation_notes", "")
                domain = ans.get("domain", "")

                card_id = _deterministic_card_id(
                    learner_id or "generic", lx_id, q_id, metric_key
                )

                content_str = (
                    f"Quantitative Assessment [{metric_key}]: Score {score}/100. "
                    f"Response: {learner_answer[:160]}"
                )
                rationale_str = (
                    notes or f"Quantitative test score of {score}% in {metric_key}."
                )
                # Use metric_key/domain directly if they are canonical tags, else fallback
                canonical_tags = [
                    t
                    for t in [metric_key.lower(), domain.lower()]
                    if t in ALLOWED_TAXONOMY_SET
                ] or ["technical_skills"]

                if card_id not in cards_by_id:
                    associated_learners = [learner_id] if learner_id else []
                    card_obj = MemoryCard(
                        card_id=card_id,
                        metric_key=metric_key,
                        content=content_str,
                        rationale=rationale_str,
                        tags=canonical_tags,
                        created_at=(
                            record.get("terminated_at") or record.get("activated_at")
                        ),
                        associated_learner_ids=associated_learners,
                        source_datasource_id=source_datasource_id,
                    )
                    cards_by_id[card_id] = card_obj.model_dump(
                        exclude={"profile_hints", "meeting_id"}
                    )
                else:
                    existing_learners = cards_by_id[card_id]["associated_learner_ids"]
                    if learner_id and learner_id not in existing_learners:
                        existing_learners.append(learner_id)

    return list(cards_by_id.values())


def extract_memory_cards_from_reviews(
    reviews_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    cards_by_id: Dict[str, Dict[str, Any]] = {}

    for record in reviews_data:
        learner_id = record.get("learner_id")
        lx_id = record.get("lx_id") or "review_task"
        task_headline = record.get("task_headline", "Task Review")
        verdict = record.get("verdict", "reviewed")
        feedback_summary = record.get("feedback_summary", "")
        mentor_reply = record.get("mentor_reply", "")
        timestamp = record.get("timestamp")
        attempt_number = record.get("attempt_number", 1)
        detailed_rubrics = record.get("detailed_rubric_evaluations", [])
        mentor_metrics = record.get("mentor_evaluation_metrics", {})

        source_datasource_id = DataSource.generate_deterministic_id(
            learner_id=str(learner_id),
            lx_id=str(record.get("lx_id")),
            timestamp=record.get("timestamp", "2026-08-01T00:00:00Z"),
            source_type="review",
            attempt=record.get("attempt_number", 1),
        )

        if feedback_summary or mentor_reply:
            card_id = _deterministic_card_id(
                learner_id or "generic",
                lx_id,
                "mentor_qualitative_feedback",
                str(attempt_number),
            )
            feedback_text = feedback_summary or mentor_reply
            content_str = f"Mentor Review for {task_headline}: {feedback_text}"
            rationale_str = (
                f"Mentor evaluation verdict '{verdict}' (Attempt #{attempt_number})."
            )
            canonical_tags = ["communication", "adaptability_learning"]

            if card_id not in cards_by_id:
                associated_learners = [learner_id] if learner_id else []
                card_obj = MemoryCard(
                    card_id=card_id,
                    metric_key="mentor_feedback.qualitative_summary",
                    content=content_str,
                    rationale=rationale_str,
                    tags=canonical_tags,
                    created_at=timestamp,
                    associated_learner_ids=associated_learners,
                    source_datasource_id=source_datasource_id,
                )
                cards_by_id[card_id] = card_obj.model_dump(
                    exclude={"profile_hints", "meeting_id"}
                )
            else:
                existing_learners = cards_by_id[card_id]["associated_learner_ids"]
                if learner_id and learner_id not in existing_learners:
                    existing_learners.append(learner_id)

        for rp in detailed_rubrics:
            if not isinstance(rp, dict):
                continue
            category = rp.get("category", "general_skills")
            requirement = rp.get("requirement", "")
            status = rp.get("status", "Yes")
            reason = rp.get("reason", "")
            criteria = rp.get("evaluation_criteria", "")
            rubric_id = rp.get("rubric_id") or requirement[:30]

            if reason or criteria:
                card_id = _deterministic_card_id(
                    learner_id or "generic", lx_id, "rubric_point", str(rubric_id)
                )
                content_str = f"[{status}] {requirement}: {criteria}".strip()
                rationale_str = reason or (
                    f"Evaluated as '{status}' by mentor for: {requirement}."
                )
                # Use category directly if it's a canonical tag, else fallback
                canonical_tags = (
                    [category.lower()]
                    if category.lower() in ALLOWED_TAXONOMY_SET
                    else ["problem_solving"]
                )

                if card_id not in cards_by_id:
                    associated_learners = [learner_id] if learner_id else []
                    card_obj = MemoryCard(
                        card_id=card_id,
                        metric_key=f"mentor_rubric.{category}",
                        content=content_str,
                        rationale=rationale_str,
                        tags=canonical_tags,
                        created_at=timestamp,
                        associated_learner_ids=associated_learners,
                        source_datasource_id=source_datasource_id,
                    )
                    cards_by_id[card_id] = card_obj.model_dump(
                        exclude={"profile_hints", "meeting_id"}
                    )
                else:
                    existing_learners = cards_by_id[card_id]["associated_learner_ids"]
                    if learner_id and learner_id not in existing_learners:
                        existing_learners.append(learner_id)

        if isinstance(mentor_metrics, dict):
            for metric_name, eval_info in mentor_metrics.items():
                if not isinstance(eval_info, dict):
                    continue
                score = eval_info.get("score")
                notes = eval_info.get("notes", "")
                card_id = _deterministic_card_id(
                    learner_id or "generic", "behavioral_metric", metric_name
                )
                content_str = f"Behavioral Observation [{metric_name}]: {notes}"
                rationale_str = f"Qualitative score rating: {score}/5.0"
                canonical_tags = BEHAVIOR_METRIC_TAG_MAP.get(
                    metric_name, ["adaptability_learning"]
                )

                if card_id not in cards_by_id:
                    associated_learners = [learner_id] if learner_id else []
                    card_obj = MemoryCard(
                        card_id=card_id,
                        metric_key=metric_name,
                        content=content_str,
                        rationale=rationale_str,
                        tags=canonical_tags,
                        created_at=timestamp,
                        associated_learner_ids=associated_learners,
                        source_datasource_id=source_datasource_id,
                    )
                    cards_by_id[card_id] = card_obj.model_dump(
                        exclude={"profile_hints", "meeting_id"}
                    )
                else:
                    existing_learners = cards_by_id[card_id]["associated_learner_ids"]
                    if learner_id and learner_id not in existing_learners:
                        existing_learners.append(learner_id)

    return list(cards_by_id.values())


def merge_memory_cards(
    assessment_cards: List[Dict[str, Any]],
    review_cards: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged_by_id: Dict[str, Dict[str, Any]] = {}

    for card in assessment_cards + review_cards:
        card_id = card.get("card_id")
        if not card_id:
            continue

        if card_id not in merged_by_id:
            merged_by_id[card_id] = dict(card)
        else:
            existing = merged_by_id[card_id]
            existing_learners = set(existing.get("associated_learner_ids", []))
            new_learners = set(card.get("associated_learner_ids", []))
            existing["associated_learner_ids"] = list(existing_learners | new_learners)

            combined_tags = existing.get("tags", []) + card.get("tags", [])
            existing["tags"] = canonicalize_tags(combined_tags)

    return list(merged_by_id.values())


def generate_memory_card_nodes(
    assessments_file: str = LMS_ASSESSMENTS_OUTPUT_FILE,
    rubrics_file: str = RUBRICS_OUTPUT_FILE,
    output_file: str = MEMORY_CARDS_OUTPUT_FILE,
) -> List[Dict[str, Any]]:

    assessment_cards: List[Dict[str, Any]] = []
    review_cards: List[Dict[str, Any]] = []

    if os.path.exists(assessments_file):
        with open(assessments_file, "r", encoding="utf-8") as f:
            assessments_data = json.load(f)
        assessment_cards = extract_memory_cards_from_assessments(assessments_data)
        logger.info(f"Extracted {len(assessment_cards)} quantitative assessment cards.")
    else:
        logger.warning(f"Assessments file not found: {assessments_file}")

    if os.path.exists(rubrics_file):
        with open(rubrics_file, "r", encoding="utf-8") as f:
            reviews_data = json.load(f)
        review_cards = extract_memory_cards_from_reviews(reviews_data)
        logger.info(f"Extracted {len(review_cards)} qualitative mentor review cards.")
    else:
        logger.warning(f"Rubrics file not found: {rubrics_file}")

    unified_cards = merge_memory_cards(assessment_cards, review_cards)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(unified_cards, f, indent=2, ensure_ascii=False)

    logger.info(
        f"[OK] Generated {len(unified_cards)} unified MemoryCard nodes "
        f"and saved to '{output_file}'."
    )
    return unified_cards


if __name__ == "__main__":
    generate_memory_card_nodes()
