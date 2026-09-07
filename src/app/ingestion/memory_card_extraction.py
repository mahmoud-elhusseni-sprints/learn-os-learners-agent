import json
import logging
import os
from typing import Any, Dict, List

from src.app.core.config import LMS_ASSESSMENTS_OUTPUT_FILE, MEMORY_CARDS_OUTPUT_FILE
from src.app.models.deliverables import MemoryCard

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def extract_memory_cards_from_assessments(
    assessments_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    cards_by_id: Dict[str, Dict[str, Any]] = {}

    for record in assessments_data:
        learner_id = record.get("learner_id")
        mastery_cards = record.get("mastery_memory_cards", [])

        for raw_card in mastery_cards:
            if not isinstance(raw_card, dict):
                continue

            card_id = raw_card.get("card_id")
            if not card_id:
                continue

            tags = raw_card.get("tags") or raw_card.get("profile_hints") or []
            if isinstance(tags, str):
                tags = [tags]

            if card_id not in cards_by_id:
                associated_learners = []
                if learner_id:
                    associated_learners.append(learner_id)

                card_obj = MemoryCard(
                    card_id=card_id,
                    metric_key=raw_card.get("metric_key", "general_competency"),
                    content=raw_card.get("content", ""),
                    rationale=raw_card.get("rationale"),
                    tags=list(set(tags)),
                    created_at=raw_card.get("created_at"),
                    associated_learner_ids=associated_learners,
                )
                cards_by_id[card_id] = card_obj.model_dump(
                    exclude={"profile_hints", "meeting_id"}
                )
            else:
                existing_learners = cards_by_id[card_id]["associated_learner_ids"]
                if learner_id and learner_id not in existing_learners:
                    existing_learners.append(learner_id)

    return list(cards_by_id.values())


def generate_memory_card_nodes(
    assessments_file: str = LMS_ASSESSMENTS_OUTPUT_FILE,
    output_file: str = MEMORY_CARDS_OUTPUT_FILE,
) -> List[Dict[str, Any]]:
    if not os.path.exists(assessments_file):
        logger.warning(f"Assessments file not found: {assessments_file}")
        return []

    with open(assessments_file, "r", encoding="utf-8") as f:
        assessments_data = json.load(f)

    cards = extract_memory_cards_from_assessments(assessments_data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)

    logger.info(
        f"[OK] Extracted {len(cards)} MemoryCard nodes and saved to "
        f"'{output_file}'."
    )
    return cards


if __name__ == "__main__":
    generate_memory_card_nodes()
