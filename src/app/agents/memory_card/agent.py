"""Memory Card Agent for extracting structured learner cards from
transcripts and conversations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import MemoryCardAgentConfig
from .llm_adapter import MemoryCardLLMAdapter
from .prompts import (
    SYSTEM_PROMPT,
    VALID_METRICS,
    VALID_TAGS,
    build_conversation_prompt,
    build_transcript_prompt,
)


class MemoryCardAgent:
    """Orchestrate LLM extraction and schema normalization for memory cards."""

    system_prompt = SYSTEM_PROMPT

    def __init__(
        self,
        config: Optional[MemoryCardAgentConfig] = None,
        llm_adapter: Optional[Any] = None,
    ) -> None:
        self.config = config or MemoryCardAgentConfig.from_env()
        self.llm_adapter = llm_adapter or MemoryCardLLMAdapter(self.config)

    def normalize_metric(self, metric_key: str) -> str:
        """Normalize or fallback metric key to one of VALID_METRICS."""
        if metric_key in VALID_METRICS:
            return metric_key
        # Check suffix match
        for vm in VALID_METRICS:
            if metric_key.split(".")[-1] in vm:
                return vm
        return "learning_goals.learner_tasks"

    def normalize_tags(self, raw_tags: List[Any]) -> List[str]:
        """Validate and normalize tags to only predefined VALID_TAGS."""
        validated_tags: List[str] = []
        for rt in raw_tags:
            if not isinstance(rt, str):
                continue
            clean_t = rt.strip()
            if clean_t in VALID_TAGS:
                validated_tags.append(clean_t)
            else:
                normalized_t = clean_t.replace("-", "_").lower()
                if normalized_t in VALID_TAGS:
                    validated_tags.append(normalized_t)
                else:
                    for vt in VALID_TAGS:
                        if normalized_t in vt or vt in normalized_t:
                            validated_tags.append(vt)
                            break
        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: List[str] = []
        for t in validated_tags:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
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
        """Construct a normalized memory-card dict matching the schema."""
        learner_id = learner.get("learner_id", "")
        metric_key = self.normalize_metric(item.get("metric_key", ""))
        source_locator = str(item.get("source_locator", "turn:0"))
        card_id = f"{source_id}:{learner_id}:{source_locator}:{metric_key}"

        timestamp = created_at_utc or datetime.now(timezone.utc).isoformat()
        now_iso = datetime.now(timezone.utc).isoformat()

        validated_tags = self.normalize_tags(item.get("tags", []))

        project_metadata: Dict[str, Any] = {
            "tags": validated_tags,
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
            project_metadata.update(
                {
                    "meeting_type": meeting_meta.get("kind", "meeting"),
                    "meeting_topic": meeting_meta.get("topic", group_name),
                    "zoom_meeting_id": meeting_meta.get("zoom_meeting_id"),
                    "zoom_meeting_uuid": meeting_meta.get("zoom_meeting_uuid")
                    or source_id,
                    "scheduled_meeting_id": meeting_meta.get("meeting_id"),
                    "scheduled_starts_at_utc": meeting_meta.get(
                        "starts_at_utc", timestamp
                    ),
                }
            )
        elif lx_meta:
            project_metadata.update(
                {
                    "interaction_type": lx_meta.get("flow", "lx_interaction"),
                    "lx_id": lx_meta.get("lx_id"),
                    "topic": lx_meta.get("topic", "learner_mentorship"),
                }
            )

        normalized_payload = {
            "org_id": org_id,
            "content": item.get("content", ""),
            "user_id": learner_id,
            "rationale": item.get("rationale", ""),
            "created_at": timestamp,
            "project_slug": project_slug,
            "profile_hints": [metric_key],
            "project_metadata": project_metadata,
            "response_excerpt": item.get("response_excerpt", ""),
        }

        return {
            "card_id": card_id,
            "meeting_id": meeting_id,
            "learner_id": learner_id,
            "metric_key": metric_key,
            "normalized_payload": normalized_payload,
            "delivery_status": "pending",
            "created_at": now_iso,
            "round_name": round_name,
        }

    def format_as_code(self, cards: List[Dict[str, Any]]) -> str:
        """Render card dicts as MemoryCard blocks matching schema.md format."""
        lines: List[str] = []
        for idx, card in enumerate(cards, start=1):
            payload = card.get("normalized_payload", {})
            meta = payload.get("project_metadata", {})

            card_id = card.get("card_id", "")
            meeting_id = card.get("meeting_id") or ""
            metric_key = card.get("metric_key", "")
            content = payload.get("content", "")
            rationale = payload.get("rationale", "")
            tags = meta.get("tags", [])
            created_at = card.get("created_at", "")

            lines.append(f"## {idx}. MemoryCard")
            lines.append("")
            lines.append(f'card_id="{card_id}",')
            lines.append(f'meeting_id="{meeting_id}",')
            lines.append(f'metric_key="{metric_key}",')
            lines.append("")
            lines.append("content=(")
            lines.append(f'    "{content}",')
            lines.append("),")
            lines.append("")
            lines.append("rationale=(")
            lines.append(f'    "{rationale}",')
            lines.append("),")
            lines.append("")
            lines.append("tags=[")
            for tag in tags:
                lines.append(f'    "{tag}",')
            lines.append("], # predefined")
            lines.append("")
            lines.append(f'created_at="{created_at}",')
            lines.append("")
            lines.append("")

        return "\n".join(lines)

    def build_transcript_prompt(
        self,
        group_name: str,
        meeting_topic: str,
        meeting_kind: str,
        roster_summary: str,
        content: str,
    ) -> str:
        """Build extraction prompt for meeting transcripts."""
        return build_transcript_prompt(
            group_name=group_name,
            meeting_topic=meeting_topic,
            meeting_kind=meeting_kind,
            roster_summary=roster_summary,
            content=content,
        )

    def build_conversation_prompt(
        self,
        group_name: str,
        learner_name: str,
        learner_id: str,
        learner_email: str,
        content: str,
    ) -> str:
        """Build extraction prompt for learner conversations."""
        return build_conversation_prompt(
            group_name=group_name,
            learner_name=learner_name,
            learner_id=learner_id,
            learner_email=learner_email,
            content=content,
        )

    def extract_from_transcript(
        self,
        content: str,
        group_name: str,
        meeting_topic: str,
        meeting_kind: str,
        roster_summary: str,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """Run extraction for a meeting transcript."""
        prompt = build_transcript_prompt(
            group_name=group_name,
            meeting_topic=meeting_topic,
            meeting_kind=meeting_kind,
            roster_summary=roster_summary,
            content=content,
        )
        if dry_run:
            print(f"  [Dry Run] Prepared transcript prompt ({len(prompt)} chars).")
            return []

        if hasattr(self.llm_adapter, "generate"):
            return self.llm_adapter.generate(prompt)
        return []

    def extract_from_conversation(
        self,
        content: str,
        group_name: str,
        learner_name: str,
        learner_id: str,
        learner_email: str,
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """Run extraction for a learner conversation."""
        prompt = build_conversation_prompt(
            group_name=group_name,
            learner_name=learner_name,
            learner_id=learner_id,
            learner_email=learner_email,
            content=content,
        )
        if dry_run:
            print(f"  [Dry Run] Prepared conversation prompt ({len(prompt)} chars).")
            return []

        if hasattr(self.llm_adapter, "generate"):
            return self.llm_adapter.generate(prompt)
        return []
