"""Storage-independent orchestration around the Task 10 transformation."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from src.app.models.models import LearnerProfile, MemoryCard, ProfileUpdateInput


@dataclass
class Snapshot:
    """Original persisted state, used for optimistic concurrency checks."""

    profile: LearnerProfile
    metrics_json: str
    checkpoint: str | None
    version: int


class ProfileStorage(Protocol):
    def active_ids(self) -> list[str]: ...

    def load(self, learner_id: str) -> Snapshot | None: ...

    def cards(self, learner_id: str) -> list[MemoryCard]: ...

    def save(
        self,
        learner_id: str,
        snapshot: Snapshot,
        profile: LearnerProfile,
        cutoff: datetime,
    ) -> None: ...


def update_learner(
    learner_id: str,
    storage: ProfileStorage,
    agent: Any,
    cutoff: datetime | None = None,
) -> dict[str, Any]:
    """Update one learner; failures never advance its checkpoint.

    Include unseen backdated cards: observation time is not ingestion time.
    Known evidence IDs prevent duplicates, including checkpoint boundary ties.
    """
    cutoff = cutoff or datetime.now(UTC)
    snapshot = storage.load(learner_id)
    if snapshot is None:
        return {"status": "inactive", "learner_id": learner_id}
    if snapshot.checkpoint and datetime.fromisoformat(snapshot.checkpoint) > cutoff:
        raise ValueError("Checkpoint is ahead of the current run")
    cards = []
    for card in storage.cards(learner_id):
        if card.created_at is None:
            raise ValueError("Memory card has no observation timestamp")
        previous = snapshot.profile.metrics.get(card.metric_key)
        known = previous.evidence_ids if previous else []
        if card.created_at <= cutoff and card.card_id not in known:
            cards.append(card)
    profile = snapshot.profile.model_copy(deep=True)
    if cards:
        profile = agent.update(
            ProfileUpdateInput(
                previous_profile=profile,
                memory_cards=cards,
            )
        )
        targeted = {card.metric_key for card in cards}
        old = snapshot.profile.model_dump(mode="json")
        new = profile.model_dump(mode="json")
        for key, value in old["metrics"].items():
            if key not in targeted and new["metrics"].get(key) != value:
                raise ValueError("Agent changed an untargeted metric")
        if set(new["metrics"]) - set(old["metrics"]) - targeted:
            raise ValueError("Agent created an untargeted metric")
        if {k: v for k, v in old.items() if k != "metrics"} != {
            k: v for k, v in new.items() if k != "metrics"
        }:
            raise ValueError("Agent changed learner metadata")
    storage.save(learner_id, snapshot, profile, cutoff)
    return {
        "status": "updated" if cards else "no_new_cards",
        "learner_id": learner_id,
        "card_count": len(cards),
    }
