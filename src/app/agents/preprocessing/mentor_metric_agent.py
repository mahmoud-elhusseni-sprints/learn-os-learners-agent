import json
import os
from typing import Any, Dict, List

from .llm_client import safe_llm_generate_json
from .lms_prompts import get_mentor_metric_prompt


class MentorMetricAgent:
    def evaluate_mentor_metrics_map(
        self, configs_filepath: str, logs_filepath: str
    ) -> Dict[str, Dict[str, Any]]:
        learner_eval_data: Dict[str, Dict[str, Any]] = {}

        if os.path.exists(configs_filepath):
            with open(configs_filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    learner_id = rec.get("learner_id")
                    if not learner_id:
                        continue

                    if learner_id not in learner_eval_data:
                        learner_eval_data[learner_id] = {
                            "learner_name": rec.get("learner_name", "Learner"),
                            "tasks": [],
                            "logs": [],
                            "submissions": [],
                        }

                    config_json = rec.get("config_json", {})
                    task = config_json.get("task", {})
                    learner_eval_data[learner_id]["tasks"].append(
                        {
                            "lx_id": rec.get("lx_id"),
                            "headline": task.get("headline", ""),
                            "description": task.get("description", ""),
                        }
                    )

        if os.path.exists(logs_filepath):
            with open(logs_filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    learner_id = rec.get("learner_id")
                    if not learner_id or learner_id not in learner_eval_data:
                        continue

                    entry = rec.get("entry", {})
                    if not entry:
                        continue

                    summary = entry.get("summary", "")
                    submission = entry.get("submission")
                    actor_messages = entry.get("actor_messages", [])

                    if summary:
                        learner_eval_data[learner_id]["logs"].append(summary)
                    if submission:
                        sub_text = submission.get("text", "")
                        if sub_text:
                            learner_eval_data[learner_id]["submissions"].append(sub_text[:300])
                    for msg in actor_messages:
                        text = msg.get("text", "")
                        if text:
                            learner_eval_data[learner_id]["logs"].append(text[:200])

        metrics_map: Dict[str, Dict[str, Any]] = {}
        for learner_id, data in learner_eval_data.items():
            learner_name = data["learner_name"]
            tasks = data["tasks"]
            subs = data["submissions"]
            logs = data["logs"]

            prompt = get_mentor_metric_prompt(
                learner_name=learner_name,
                learner_id=learner_id,
                tasks=tasks,
                subs=subs,
                logs=logs,
            )

            print(
                f"[Agent 2 - Mentor Metric] Evaluating metrics for learner "
                f"{learner_name} ({learner_id})..."
            )
            llm_result = safe_llm_generate_json(prompt)

            if llm_result and isinstance(llm_result, dict):
                print(
                    f"[Agent 2 - Mentor Metric] Successfully evaluated metrics "
                    f"for {learner_name}."
                )
                metrics_map[learner_id] = llm_result
            else:
                print(
                    f"[Agent 2 - Mentor Metric] LLM returned invalid format or "
                    f"failed for {learner_name}."
                )
                metrics_map[learner_id] = {}

        return metrics_map
