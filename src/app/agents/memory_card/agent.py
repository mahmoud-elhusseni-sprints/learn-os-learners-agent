from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .llm_adapter import MemoryCardLLMAdapter
from .prompts import (
    SYSTEM_PROMPT,
    VALID_METRICS,
    VALID_TAGS,
    build_conversation_prompt,
    build_transcript_prompt,
)


class MemoryCardAgent:

    system_prompt = SYSTEM_PROMPT

    def __init__(self, llm_adapter: Optional[Any] = None) -> None:
        self.llm_adapter = llm_adapter or MemoryCardLLMAdapter()

    def normalize_metric(self, metric_key: str) -> str:
        if metric_key in VALID_METRICS:
            return metric_key
        key_suffix = metric_key.split(".")[-1]
        return next((vm for vm in VALID_METRICS if key_suffix in vm), "learning_goals.learner_tasks")

    def normalize_tags(self, raw_tags: List[Any]) -> List[str]:
        deduped: List[str] = []
        for rt in raw_tags:
            if not isinstance(rt, str):
                continue
            
            clean_t = rt.strip()
            norm_t = clean_t.replace("-", "_").lower()

            matched = None
            if clean_t in VALID_TAGS:
                matched = clean_t
            elif norm_t in VALID_TAGS:
                matched = norm_t
            else:
                matched = next((vt for vt in VALID_TAGS if norm_t in vt or vt in norm_t), None)

            if matched and matched not in deduped:
                deduped.append(matched)

        return deduped

    def build_card(
        self,
        item: Dict[str, Any],
        learner: Dict[str, Any],
        group_id: str,
        group_name: str,
        org_id: str,
        round_name: str,
        source_type: str,
        workflow: str,
        source_id: str,
        project_slug: str,
        meeting_meta: Optional[Dict[str, Any]] = None,
        lx_meta: Optional[Dict[str, Any]] = None,
        created_at_utc: Optional[str] = None,
    ) -> Dict[str, Any]:

        learner_id = learner.get("learner_id", "")
        metric_key = self.normalize_metric(item.get("metric_key", ""))
        source_locator = str(item.get("source_locator", "turn:0"))
        
        timestamp = created_at_utc or datetime.now(timezone.utc).isoformat()
        now_iso = datetime.now(timezone.utc).isoformat()
        card_id = f"{source_id}:{learner_id}:{source_locator}:{metric_key}"

        project_metadata: Dict[str, Any] = {
            "tags": self.normalize_tags(item.get("tags", [])),
            "card_id": card_id,
            "group_id": group_id,
            "workflow": workflow,
            "source_id": source_id,
            "confidence": float(item.get("confidence", 0.95)),
            "source_type": source_type,
            "source_locator": source_locator,
        }

        meeting_id = None
        if meeting_meta:
            meeting_id = meeting_meta.get("meeting_id")
            project_metadata.update({
                "meeting_type": meeting_meta.get("kind", "meeting"),
                "meeting_topic": meeting_meta.get("topic", group_name),
                "zoom_meeting_id": meeting_meta.get("zoom_meeting_id"),
                "zoom_meeting_uuid": meeting_meta.get("zoom_meeting_uuid") or source_id,
                "scheduled_meeting_id": meeting_id,
                "scheduled_starts_at_utc": meeting_meta.get("starts_at_utc", timestamp),
            })
        elif lx_meta:
            project_metadata.update({
                "interaction_type": lx_meta.get("flow", "lx_interaction"),
                "lx_id": lx_meta.get("lx_id"),
                "topic": lx_meta.get("topic", "learner_mentorship"),
            })

        return {
            "card_id": card_id,
            "meeting_id": meeting_id,
            "learner_id": learner_id,
            "metric_key": metric_key,
            "normalized_payload": {
                "org_id": org_id,
                "content": item.get("content", ""),
                "user_id": learner_id,
                "rationale": item.get("rationale", ""),
                "created_at": timestamp,
                "project_slug": project_slug,
                "profile_hints": [metric_key],
                "project_metadata": project_metadata,
                "response_excerpt": item.get("response_excerpt", ""),
            },
            "delivery_status": "pending",
            "created_at": now_iso,
            "round_name": round_name,
        }

    def format_as_code(self, cards: List[Dict[str, Any]]) -> str:
        blocks = []
        for idx, card in enumerate(cards, start=1):
            payload = card.get("normalized_payload", {})
            meta = payload.get("project_metadata", {})
            formatted_tags = "\n".join(f'    "{t}",' for t in meta.get("tags", []))

            block = (
                f"## {idx}. MemoryCard\n\n"
                f'card_id="{card.get("card_id", "")}",\n'
                f'meeting_id="{card.get("meeting_id") or ""}",\n'
                f'metric_key="{card.get("metric_key", "")}",\n\n'
                f'content=(\n    "{payload.get("content", "")}",\n),\n\n'
                f'rationale=(\n    "{payload.get("rationale", "")}",\n),\n\n'
                f'tags=[\n{formatted_tags}\n], # predefined\n\n'
                f'created_at="{card.get("created_at", "")}",\n\n'
            )
            blocks.append(block)
            
        return "\n".join(blocks)


    def extract_from_transcript(self, **kwargs: Any) -> List[Dict[str, Any]]:
        dry_run = kwargs.pop("dry_run", False)
        prompt = build_transcript_prompt(**kwargs)
        return self._execute(prompt, dry_run=dry_run)

    def extract_from_conversation(self, **kwargs: Any) -> List[Dict[str, Any]]:
        dry_run = kwargs.pop("dry_run", False)
        prompt = build_conversation_prompt(**kwargs)
        return self._execute(prompt, dry_run=dry_run)

    def _execute(self, prompt: str, dry_run: bool) -> List[Dict[str, Any]]:
        if dry_run:
            print(f"  [Dry Run] Prepared prompt ({len(prompt)} chars).")
            return []
        return self.llm_adapter.generate(prompt) if hasattr(self.llm_adapter, "generate") else []