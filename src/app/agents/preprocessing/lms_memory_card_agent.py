import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .llm_client import safe_llm_generate_json
from .lms_prompts import get_lms_memory_card_prompt


class LMSMemoryCardAgent:
    def __init__(self, catalog_filepath: str) -> None:
        self.catalog_filepath = catalog_filepath
        self.questions = self._load_catalog(catalog_filepath)

    def _load_catalog(self, filepath: str) -> List[Dict[str, Any]]:
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_learner_evidence(
        self, configs_filepath: str, logs_filepath: str
    ) -> Dict[str, Dict[str, Any]]:
        learner_data: Dict[str, Dict[str, Any]] = {}

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

                    if learner_id not in learner_data:
                        learner_data[learner_id] = {
                            "learner_name": rec.get("learner_name", "Learner"),
                            "tasks": [],
                            "logs": [],
                            "submissions": [],
                            "outcomes": [],
                        }

                    config_json = rec.get("config_json", {})
                    task = config_json.get("task", {})
                    learner_data[learner_id]["tasks"].append(
                        {
                            "lx_id": rec.get("lx_id"),
                            "headline": task.get("headline", ""),
                            "description": task.get("description", ""),
                            "functional_reqs": task.get("functional_requirements", []),
                            "outcome": rec.get("outcome"),
                            "status": rec.get("status"),
                        }
                    )
                    if rec.get("outcome"):
                        learner_data[learner_id]["outcomes"].append(rec.get("outcome"))

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
                    if not learner_id or learner_id not in learner_data:
                        continue

                    entry = rec.get("entry", {})
                    if not entry:
                        continue

                    summary = entry.get("summary", "")
                    submission = entry.get("submission")
                    actor_messages = entry.get("actor_messages", [])

                    if summary:
                        learner_data[learner_id]["logs"].append(summary)

                    if submission:
                        sub_text = submission.get("text", "")
                        if sub_text:
                            learner_data[learner_id]["submissions"].append(
                                sub_text[:300]
                            )

                    for msg in actor_messages:
                        text = msg.get("text", "")
                        if text:
                            learner_data[learner_id]["logs"].append(text[:200])

        return learner_data

    def generate_memory_cards_map(
        self, configs_filepath: str, logs_filepath: str, cards_per_learner: int = 15
    ) -> Dict[str, List[Dict[str, Any]]]:
        learner_evidence = self._extract_learner_evidence(
            configs_filepath, logs_filepath
        )
        cards_map: Dict[str, List[Dict[str, Any]]] = {}

        if not self.questions:
            return cards_map

        for learner_id, data in learner_evidence.items():
            learner_name = data["learner_name"]
            tasks = data["tasks"]
            logs = data["logs"]
            subs = data["submissions"]

            prompt = get_lms_memory_card_prompt(
                learner_name=learner_name,
                learner_id=learner_id,
                questions=self.questions,
                tasks=tasks,
                subs=subs,
                logs=logs,
                cards_per_learner=cards_per_learner,
            )

            print(
                f"[Agent 1 - LMS Card] Generating cards for learner "
                f"{learner_name} ({learner_id})..."
            )
            llm_result = safe_llm_generate_json(prompt)
            learner_cards = []

            if not llm_result or not isinstance(llm_result, list):
                print(
                    f"[Agent 1 - LMS Card] LLM generation failed or returned "
                    f"invalid format for {learner_name}."
                )
                cards_map[learner_id] = []
                continue

            for idx, item in enumerate(llm_result):
                card_uuid = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_DNS,
                        f"{learner_id}:{item.get('metric_key')}:{idx}",
                    )
                )
                lx_id = (
                    tasks[idx % len(tasks)]["lx_id"]
                    if tasks
                    else str(uuid.uuid4())
                )

                card = {
                    "card_id": card_uuid,
                    "meeting_id": lx_id,
                    "metric_key": item.get(
                        "metric_key",
                        self.questions[idx % len(self.questions)]["metric_key"],
                    ),
                    "content": item.get("content", ""),
                    "rationale": item.get("rationale", ""),
                    "profile_hints": item.get("profile_hints", []),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                learner_cards.append(card)

            print(
                f"[Agent 1 - LMS Card] Successfully generated "
                f"{len(learner_cards)} cards for {learner_name}."
            )
            cards_map[learner_id] = learner_cards

        return cards_map
