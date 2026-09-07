import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def build_attempt_map(turns_filepath: str) -> Dict[str, int]:
    attempt_map: Dict[str, int] = {}
    if not os.path.exists(turns_filepath):
        logger.warning(f"Turns file not found: {turns_filepath}")
        return attempt_map

    with open(turns_filepath, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                if not isinstance(record, dict):
                    logger.warning(
                        f"Line {line_idx} in {turns_filepath} is not a " f"JSON object"
                    )
                    continue
            except json.JSONDecodeError as err:
                logger.error(
                    f"Malformed JSON on line {line_idx} in {turns_filepath}: {err}"
                )
                continue

            lx_id = record.get("lx_id")
            n8n_meta = record.get("n8n_meta", {})
            attempt = n8n_meta.get("attempt") if isinstance(n8n_meta, dict) else None

            if lx_id and attempt is not None:
                attempt_map[lx_id] = max(attempt_map.get(lx_id, 0), attempt)
            elif not lx_id:
                logger.warning(f"Line {line_idx} in {turns_filepath} missing 'lx_id'")

    return attempt_map


def build_deadline_map(configs_filepath: str) -> Dict[str, str]:
    deadline_map: Dict[str, str] = {}
    if not os.path.exists(configs_filepath):
        logger.warning(f"Configs file not found: {configs_filepath}")
        return deadline_map

    with open(configs_filepath, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                if not isinstance(record, dict):
                    continue
            except json.JSONDecodeError:
                continue

            lx_id = record.get("lx_id")
            deadline_at = record.get("deadline_at")
            if lx_id and deadline_at:
                deadline_map[lx_id] = deadline_at

    return deadline_map


def compute_timeliness(
    sub_ts_str: Optional[str], deadline_ts_str: Optional[str]
) -> Optional[float]:
    if not sub_ts_str or not deadline_ts_str:
        return None
    try:
        sub_dt = datetime.fromisoformat(sub_ts_str.replace("Z", "+00:00"))
        dead_dt = datetime.fromisoformat(deadline_ts_str.replace("Z", "+00:00"))
        diff_seconds = (dead_dt - sub_dt).total_seconds()
        return round(diff_seconds / 3600.0, 2)
    except Exception as err:
        logger.error(
            f"Error computing timeliness for sub={sub_ts_str}, "
            f"dead={deadline_ts_str}: {err}"
        )
        return None


def extract_rubric_taxonomies(configs_filepath: str) -> Dict[str, Dict[str, Any]]:
    rubric_taxonomies: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(configs_filepath):
        logger.warning(f"Configs file not found: {configs_filepath}")
        return rubric_taxonomies

    with open(configs_filepath, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                if not isinstance(record, dict):
                    logger.warning(
                        f"Line {line_idx} in {configs_filepath} is not a "
                        f"JSON object"
                    )
                    continue
            except json.JSONDecodeError as err:
                logger.error(
                    f"Malformed JSON on line {line_idx} in {configs_filepath}: {err}"
                )
                continue

            lx_id = record.get("lx_id")
            config_json = record.get("config_json", {})
            task = config_json.get("task", {}) if isinstance(config_json, dict) else {}

            if lx_id and task:
                headline = task.get("headline", "")
                description = task.get("description", "")
                rubric = task.get("rubric", {}) if isinstance(task, dict) else {}

                scopes = rubric.get("scopes", []) if isinstance(rubric, dict) else []
                quality_criteria = (
                    task.get("quality_criteria", []) if isinstance(task, dict) else []
                )

                tax_record = {
                    "lx_id": lx_id,
                    "task_headline": headline,
                    "task_description": description,
                    "functional_requirements": task.get("functional_requirements", []),
                    "rubric_scopes": scopes,
                    "quality_criteria": quality_criteria,
                }

                rubric_taxonomies[lx_id] = tax_record
            elif not lx_id:
                logger.warning(
                    f"Line {line_idx} in {configs_filepath} missing "
                    f"mandatory key 'lx_id'"
                )

    return rubric_taxonomies


def parse_feedback_raw(
    raw_text: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not raw_text:
        return [], []

    scope_results: List[Dict[str, Any]] = []
    quality_results: List[Dict[str, Any]] = []
    decoder = json.JSONDecoder()

    if "Scope Detailed Results:" in raw_text:
        try:
            part = raw_text.split("Scope Detailed Results:")[1].strip()
            scope_results, _ = decoder.raw_decode(part)
        except Exception as err:
            logger.warning(f"Failed to decode Scope Detailed Results: {err}")

    if "Quality Detailed Results:" in raw_text:
        try:
            part = raw_text.split("Quality Detailed Results:")[1].strip()
            quality_results, _ = decoder.raw_decode(part)
        except Exception as err:
            logger.warning(f"Failed to decode Quality Detailed Results: {err}")

    return scope_results, quality_results


def extract_mentor_evaluations(
    logs_filepath: str,
    attempt_map: Dict[str, int],
    taxonomies: Dict[str, Dict[str, Any]],
    deadline_map: Optional[Dict[str, str]] = None,
    metrics_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    extracted_evaluations: List[Dict[str, Any]] = []
    if deadline_map is None:
        deadline_map = {}
    if metrics_map is None:
        metrics_map = {}

    if not os.path.exists(logs_filepath):
        logger.warning(f"Logs file not found: {logs_filepath}")
        return extracted_evaluations

    submissions_by_attempt: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
    with open(logs_filepath, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                if not isinstance(record, dict):
                    continue
            except json.JSONDecodeError:
                continue

            entry = record.get("entry", {})
            if not isinstance(entry, dict):
                continue

            submission_data = entry.get("submission")
            if submission_data and isinstance(submission_data, dict):
                learner_id = record.get("learner_id")
                lx_id = record.get("lx_id")
                if not learner_id or not lx_id:
                    continue

                timestamp = entry.get("ts", "")
                attempt_number = attempt_map.get(lx_id, 1)
                sub_text = (
                    submission_data.get("text")
                    or submission_data.get("submission_content", "")
                    or ""
                )
                sub_attachments = submission_data.get("attachments", []) or []

                file_urls = [
                    att.get("url") or att.get("file_url")
                    for att in sub_attachments
                    if isinstance(att, dict)
                ]
                if not file_urls and sub_text:
                    file_urls = re.findall(r"https?://[^\s]+", sub_text)

                key = (learner_id, lx_id, attempt_number)
                if key not in submissions_by_attempt:
                    deadline_at = deadline_map.get(lx_id)
                    hours_before = (
                        compute_timeliness(timestamp, deadline_at)
                        if timestamp and deadline_at
                        else None
                    )
                    submissions_by_attempt[key] = {
                        "submission_text": sub_text,
                        "assets": [u for u in file_urls if u],
                        "hours_before_deadline": hours_before,
                    }
                else:
                    for u in file_urls:
                        if u and u not in submissions_by_attempt[key]["assets"]:
                            submissions_by_attempt[key]["assets"].append(u)
                    if sub_text and not submissions_by_attempt[key]["submission_text"]:
                        submissions_by_attempt[key]["submission_text"] = sub_text

    with open(logs_filepath, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
                if not isinstance(record, dict):
                    continue
            except json.JSONDecodeError:
                continue

            entry = record.get("entry", {})
            if not isinstance(entry, dict):
                continue

            feedback = entry.get("feedback")
            if feedback:
                learner_id = record.get("learner_id")
                lx_id = record.get("lx_id")
                timestamp = entry.get("ts")

                if not learner_id or not lx_id:
                    continue

                attempt_number = attempt_map.get(lx_id, 1)
                taxonomy = taxonomies.get(lx_id, {})

                verdict = (
                    feedback.get("verdict", "reviewed")
                    if isinstance(feedback, dict)
                    else "reviewed"
                )
                summary = (
                    feedback.get("summary", "") if isinstance(feedback, dict) else ""
                )
                mentor_reply = (
                    feedback.get("mentor_reply", "")
                    if isinstance(feedback, dict)
                    else ""
                )

                raw_text = feedback.get("raw", "") if isinstance(feedback, dict) else ""
                scope_results, quality_results = parse_feedback_raw(raw_text)

                detailed_point_scores = []
                for s in scope_results:
                    if not isinstance(s, dict):
                        continue
                    category = s.get("category", "general")
                    requirement = s.get("requirement", "")
                    for p in s.get("points", []):
                        if not isinstance(p, dict):
                            continue
                        detailed_point_scores.append(
                            {
                                "rubric_id": p.get("rubric_id"),
                                "category": category,
                                "requirement": requirement,
                                "status": p.get("status"),
                                "evaluation_criteria": p.get("evaluation_criteria"),
                                "reason": p.get("reason"),
                                "confidence_score": p.get("confidence_score"),
                            }
                        )

                sub_info = submissions_by_attempt.get(
                    (learner_id, lx_id, attempt_number), {}
                )

                eval_record = {
                    "learner_id": learner_id,
                    "lx_id": lx_id,
                    "task_headline": taxonomy.get("task_headline", ""),
                    "attempt_number": attempt_number,
                    "hours_before_deadline": sub_info.get("hours_before_deadline"),
                    "submission_text": sub_info.get("submission_text", ""),
                    "assets": sub_info.get("assets", []),
                    "timestamp": timestamp or "",
                    "verdict": verdict,
                    "feedback_summary": summary,
                    "mentor_reply": mentor_reply,
                    "detailed_rubric_evaluations": detailed_point_scores,
                    "detailed_quality_evaluations": quality_results,
                }

                learner_metrics = metrics_map.get(learner_id, {})
                if learner_metrics:
                    eval_record["mentor_evaluation_metrics"] = learner_metrics

                extracted_evaluations.append(eval_record)

    return extracted_evaluations
