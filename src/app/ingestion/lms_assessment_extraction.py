import json
import logging
import os
from typing import Any, Dict, List, Optional, Set, Union

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def _extract_score_and_topic(record: Dict[str, Any]) -> Dict[str, Any]:
    config_json = record.get("config_json", {})
    task = config_json.get("task", {}) if isinstance(config_json, dict) else {}

    topic_id = (
        record.get("topic_id")
        or task.get("task_archetype_id")
        or record.get("task_archetype_id")
        or record.get("flow_id")
    )
    topic_title = (
        record.get("topic_title")
        or task.get("description")
        or task.get("headline", "")
    )

    score = record.get("score")
    max_score = record.get("max_score", 100.0)
    score_percentage = record.get("score_percentage")

    if score is None:
        outcome = record.get("outcome", "")
        if outcome == "completed_success":
            score = 100.0
        elif outcome in ["failed", "retry"]:
            score = 0.0

    if score is not None and score_percentage is None and max_score:
        score_percentage = round((score / max_score) * 100.0, 2)

    return {
        "topic_id": topic_id,
        "topic_title": topic_title,
        "score": score,
        "max_score": max_score,
        "score_percentage": score_percentage,
    }


def _load_lx_configs(
    configs_input: Union[str, List[Any], Dict[str, Any]],
    target_lx_ids: Optional[Union[Set[str], List[str]]] = None,
    cohort_group: Optional[Union[str, List[str], Set[str]]] = None,
) -> Dict[Any, Dict[str, Any]]:
    raw_records = []

    if isinstance(configs_input, str):
        if os.path.exists(configs_input):
            with open(configs_input, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f, 1):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        parsed = json.loads(line_str)
                        if not isinstance(parsed, dict):
                            logger.warning(
                                f"Line {line_idx} in {configs_input} is not a "
                                f"JSON object: {line_str[:50]}"
                            )
                            continue
                        raw_records.append(parsed)
                    except json.JSONDecodeError as err:
                        logger.error(
                            f"Malformed JSON on line {line_idx} in "
                            f"{configs_input}: {err}"
                        )
                        continue
        else:
            logger.warning(f"Config path does not exist: {configs_input}")
    elif isinstance(configs_input, list):
        for idx, item in enumerate(configs_input):
            if not isinstance(item, dict):
                logger.warning(
                    f"Record at index {idx} in configs_input is malformed "
                    f"(not dict): {item}"
                )
                continue
            raw_records.append(item)
    elif isinstance(configs_input, dict):
        if "lx_id" in configs_input:
            raw_records = [configs_input]
        else:
            raw_records = list(configs_input.values())

    target_lx_set = set(target_lx_ids) if target_lx_ids else None

    matching_configs: Dict[Any, Dict[str, Any]] = {}
    for rec in raw_records:
        lx_id = rec.get("lx_id")
        learner_id = rec.get("learner_id")

        if not lx_id:
            logger.warning(f"Skipping record missing 'lx_id': {rec}")
            continue

        if target_lx_set and lx_id not in target_lx_set:
            continue

        if cohort_group:
            group_name = rec.get("group_name", "")
            group_id = rec.get("group_id", "")
            if isinstance(cohort_group, (list, set, tuple)):
                if group_name not in cohort_group and group_id not in cohort_group:
                    continue
            else:
                if (
                    cohort_group != group_name
                    and cohort_group != group_id
                    and cohort_group.lower() not in group_name.lower()
                    and cohort_group.lower() not in group_id.lower()
                ):
                    continue

        if learner_id:
            matching_configs[(lx_id, learner_id)] = rec
        if lx_id not in matching_configs:
            matching_configs[lx_id] = rec

    return matching_configs


def extract_lms_assessments(
    configs_filepath_or_records: Optional[Union[str, List[Any], Dict[str, Any]]] = None,
    cards_map: Optional[Dict[str, List[Any]]] = None,
    target_lx_ids: Optional[Union[Set[str], List[str]]] = None,
    cohort_group: Optional[Union[str, List[str], Set[str]]] = None,
    mock_assessments: Optional[List[Dict[str, Any]]] = None,
    answers_filepath_or_records: Optional[Union[str, List[Any]]] = None,
) -> List[Dict[str, Any]]:
    if cards_map is None:
        cards_map = {}

    assessments: List[Dict[str, Any]] = []
    seen_unique_keys = set()

    if answers_filepath_or_records is not None:
        raw_answers = []
        if (
            isinstance(answers_filepath_or_records, str)
            and os.path.exists(answers_filepath_or_records)
        ):
            with open(answers_filepath_or_records, "r", encoding="utf-8") as f:
                raw_answers = json.load(f)
        elif isinstance(answers_filepath_or_records, list):
            raw_answers = answers_filepath_or_records

        for ans in raw_answers:
            if not isinstance(ans, dict):
                continue
            learner_id = ans.get("learner_id")
            lx_id = ans.get("lx_id")
            if not learner_id or not lx_id:
                continue

            dedup_key = (learner_id, lx_id)
            if dedup_key in seen_unique_keys:
                continue

            score = ans.get("score")
            max_score = ans.get("max_score", 100.0)
            score_pct = ans.get("score_percentage")
            if score_pct is None and score is not None and max_score:
                score_pct = round((score / max_score) * 100.0, 2)

            learner_cards = (
                ans.get("mastery_memory_cards")
                or cards_map.get(learner_id, [])
            )

            assessment_record = {
                "learner_id": learner_id,
                "lx_id": lx_id,
                "assessment_type": ans.get("assessment_type", "post_course"),
                "phase": ans.get("phase"),
                "module_title": ans.get("module_title", "LMS Assessment"),
                "topic_id": ans.get("topic_id", "baseline_competency"),
                "topic_title": ans.get("topic_title", "Competency Assessment"),
                "status": ans.get("status", "terminated"),
                "outcome": ans.get("outcome", "completed_success"),
                "score": score,
                "max_score": max_score,
                "score_percentage": score_pct,
                "trial_count": ans.get("trial_count", 0),
                "extension_used": ans.get("extension_used", False),
                "activated_at": ans.get("activated_at"),
                "terminated_at": ans.get("terminated_at"),
                "answers": ans.get("answers", []),
                "mastery_memory_cards": learner_cards,
            }
            seen_unique_keys.add(dedup_key)
            assessments.append(assessment_record)

        return assessments

    config_map = (
        _load_lx_configs(
            configs_filepath_or_records,
            target_lx_ids=target_lx_ids,
            cohort_group=cohort_group,
        )
        if configs_filepath_or_records
        else {}
    )

    if mock_assessments is not None:
        target_lx_set = set(target_lx_ids) if target_lx_ids else None

        for mock_idx, mock in enumerate(mock_assessments):
            if not isinstance(mock, dict):
                logger.error(f"Malformed mock assessment at index {mock_idx}: {mock}")
                continue

            lx_id = mock.get("lx_id")
            learner_id = mock.get("learner_id")

            if not lx_id or not learner_id:
                logger.warning(
                    f"Malformed mock assessment missing ID: {mock}"
                )
                continue

            dedup_key = (learner_id, lx_id)
            if dedup_key in seen_unique_keys:
                logger.info(
                    f"Idempotent skip: Duplicate mock key {dedup_key}"
                )
                continue

            if target_lx_set and lx_id not in target_lx_set:
                continue

            matched_config = (
                config_map.get((lx_id, learner_id))
                or config_map.get(lx_id, {})
            )

            config_json = matched_config.get("config_json", {})
            task = (
                config_json.get("task", {})
                if isinstance(config_json, dict)
                else {}
            )

            headline = (
                mock.get("module_title")
                or task.get("headline", "")
                or matched_config.get("headline", "")
            )
            trial_count = mock.get(
                "trial_count", matched_config.get("trial_count", 0)
            )
            extension_used = mock.get(
                "extension_used", matched_config.get("extension_used", False)
            )
            outcome = mock.get(
                "outcome", matched_config.get("outcome", "in_progress")
            )
            status = mock.get("status", matched_config.get("status", "active"))
            activated_at = mock.get(
                "activated_at", matched_config.get("activated_at")
            )
            terminated_at = mock.get(
                "terminated_at", matched_config.get("terminated_at")
            )

            score_topic_data = _extract_score_and_topic(matched_config)
            learner_cards = cards_map.get(
                learner_id, mock.get("mastery_memory_cards", [])
            )

            final_score = (
                mock.get("score")
                if mock.get("score") is not None
                else score_topic_data["score"]
            )
            final_max_score = (
                mock.get("max_score")
                or score_topic_data["max_score"]
                or 100.0
            )
            final_score_pct = mock.get("score_percentage")
            if (
                final_score_pct is None
                and final_score is not None
                and final_max_score
            ):
                final_score_pct = round(
                    (final_score / final_max_score) * 100.0, 2
                )

            assessment_record = {
                "learner_id": learner_id,
                "lx_id": lx_id,
                "assessment_type": mock.get("assessment_type", "post_course"),
                "phase": mock.get("phase"),
                "module_title": headline,
                "topic_id": mock.get("topic_id") or score_topic_data["topic_id"],
                "topic_title": (
                    mock.get("topic_title") or score_topic_data["topic_title"]
                ),
                "status": status,
                "outcome": outcome,
                "score": final_score,
                "max_score": final_max_score,
                "score_percentage": final_score_pct,
                "trial_count": trial_count,
                "extension_used": extension_used,
                "activated_at": activated_at,
                "terminated_at": terminated_at,
                "answers": mock.get("answers", []),
                "mastery_memory_cards": learner_cards,
            }

            seen_unique_keys.add(dedup_key)
            assessments.append(assessment_record)

    elif not answers_filepath_or_records and config_map:
        processed_records = []
        seen = set()

        for record in config_map.values():
            rec_id = id(record)
            if rec_id in seen:
                continue
            seen.add(rec_id)
            processed_records.append(record)

        for record in processed_records:
            lx_id = record.get("lx_id")
            learner_id = record.get("learner_id")

            if not lx_id or not learner_id:
                logger.warning(
                    f"Skipping malformed config record missing ID: {record}"
                )
                continue

            dedup_key = (learner_id, lx_id)
            if dedup_key in seen_unique_keys:
                logger.info(
                    f"Idempotent skip: Duplicate config key {dedup_key}"
                )
                continue

            config_json = record.get("config_json", {})
            task = config_json.get("task", {}) if isinstance(config_json, dict) else {}

            headline = task.get("headline", "")
            trial_count = record.get("trial_count", 0)
            extension_used = record.get("extension_used", False)
            outcome = record.get("outcome", "in_progress")
            status = record.get("status", "active")
            activated_at = record.get("activated_at")
            terminated_at = record.get("terminated_at")

            score_topic_data = _extract_score_and_topic(record)
            learner_cards = cards_map.get(learner_id, [])

            assessment_record = {
                "learner_id": learner_id,
                "lx_id": lx_id,
                "assessment_type": "module_assessment",
                "phase": "intermediate",
                "module_title": headline,
                "topic_id": score_topic_data["topic_id"],
                "topic_title": score_topic_data["topic_title"],
                "status": status,
                "outcome": outcome,
                "score": score_topic_data["score"],
                "max_score": score_topic_data["max_score"],
                "score_percentage": score_topic_data["score_percentage"],
                "trial_count": trial_count,
                "extension_used": extension_used,
                "activated_at": activated_at,
                "terminated_at": terminated_at,
                "answers": [],
                "mastery_memory_cards": learner_cards,
            }

            seen_unique_keys.add(dedup_key)
            assessments.append(assessment_record)

    return assessments
