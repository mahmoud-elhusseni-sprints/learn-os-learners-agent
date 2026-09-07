import json
import logging
import os
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def extract_learner_profiles(filepath_list: List[str]) -> List[Dict[str, Any]]:
    profiles: List[Dict[str, Any]] = []
    seen_ids = set()

    for filepath in filepath_list:
        if not os.path.exists(filepath):
            alt_path = filepath.replace("data/", "")
            if os.path.exists(alt_path):
                filepath = alt_path
            else:
                logger.warning(f"Learner profiles file not found: {filepath}")
                continue

        with open(filepath, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, 1):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    record = json.loads(line_str)
                    if not isinstance(record, dict):
                        logger.warning(f"Line {line_idx} in {filepath} is not a JSON object: {line_str[:50]}")
                        continue
                except json.JSONDecodeError as err:
                    logger.error(f"Malformed JSON line {line_idx} in {filepath}: {err}")
                    continue

                learner_id = record.get("learner_id")
                if not learner_id:
                    logger.warning(f"Line {line_idx} in {filepath} missing mandatory key 'learner_id'")
                    continue

                if learner_id not in seen_ids:
                    seen_ids.add(learner_id)

                    profile_record = {
                        "learner_id": learner_id,
                        "name": record.get("name"),
                        "role": record.get("role"),
                        "group_name": record.get("group_name"),
                        "round_name": record.get("round_name") or record.get("round"),
                        "added_at": record.get("added_at"),
                        "learner_status": record.get("learner_status"),
                    }
                    profiles.append(profile_record)

    return profiles
