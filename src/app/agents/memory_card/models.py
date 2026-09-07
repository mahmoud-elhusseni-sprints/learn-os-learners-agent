"""Data models for Memory Card Agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RawExtractedItem(BaseModel):
    """Raw item extracted by the LLM from transcript or chat content."""

    learner_name_or_id: Optional[str] = Field(
        None, description="Learner pseudonym or UUID as identified in text"
    )
    metric_key: str = Field(
        "learning_goals.learner_tasks", description="Target metric key category"
    )
    content: str = Field(
        "", description="Factual 1-2 sentence summary of observed signal"
    )
    rationale: str = Field(
        "", description="Explanation why excerpt supports the memory card"
    )
    response_excerpt: str = Field(
        "", description="Verbatim quote from the transcript or conversation"
    )
    source_locator: str = Field(
        "turn:0", description="Turn identifier, timestamp, or line reference"
    )
    tags: List[str] = Field(
        default_factory=list, description="List of competency tags"
    )
    confidence: float = Field(
        0.95, description="Confidence score for the extraction (0.0 to 1.0)"
    )


class MemoryCardRecord(BaseModel):
    """Normalized Memory Card representation matching meeting_memory_cards.jsonl."""

    card_id: str
    meeting_id: Optional[str] = None
    learner_id: str
    metric_key: str
    normalized_payload: Dict[str, Any]
    delivery_status: str = "pending"
    created_at: str
    round_name: str
