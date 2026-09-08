"""Selective, non-persistent profile transformation with an injected AI layer."""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from .models import (
    LearnerProfile,
    MemoryCard,
    MetricDraft,
    ProfileMetric,
    ProfileUpdateInput,
)


class ProfileUpdateError(RuntimeError):
    """The transformation failed; no partial profile should be persisted."""


class MetricSynthesizer(Protocol):
    """Replaceable boundary between deterministic merge logic and the LLM."""

    def synthesize(
        self,
        metric_key: str,
        previous: ProfileMetric | None,
        cards: list[MemoryCard],
    ) -> MetricDraft:
        """Produce one grounded metric draft without storage side effects."""
        ...


class LearnerProfileUpdateAgent:
    """Update exactly the card targets; never mutate the caller's input.

    The LLM sees one targeted baseline at a time. Python controls target keys,
    evidence IDs, preservation and the final validated output. All targets must
    succeed before a profile is returned. No database or filesystem operations.
    """

    def __init__(self, synthesizer: MetricSynthesizer) -> None:
        self.synthesizer = synthesizer

    def update(self, request: ProfileUpdateInput) -> LearnerProfile:
        """Return a deep-copied updated profile or raise ProfileUpdateError.

        Exact duplicate cards and already-recorded IDs are not synthesized again.
        Conflicting payloads sharing a card ID in this batch are rejected.
        """
        request = request.model_copy(deep=True)
        result = (
            request.previous_profile.model_copy(deep=True)
            if request.previous_profile is not None
            else LearnerProfile()
        )
        unique: dict[str, MemoryCard] = {}
        for card in request.memory_cards:
            if card.card_id in unique and unique[card.card_id] != card:
                raise ProfileUpdateError("Conflicting memory cards share a card_id.")
            unique[card.card_id] = card

        groups: dict[str, list[MemoryCard]] = defaultdict(list)
        for card in unique.values():
            groups[card.metric_key].append(card)

        for key, cards in groups.items():
            previous = result.metrics.get(key)
            old_ids = list(previous.evidence_ids) if previous else []
            fresh = sorted(
                (card for card in cards if card.card_id not in old_ids),
                key=lambda card: (card.created_at, card.card_id),
            )
            if not fresh:
                continue
            try:
                raw = self.synthesizer.synthesize(
                    key,
                    previous.model_copy(deep=True) if previous else None,
                    [card.model_copy(deep=True) for card in fresh],
                )
                # Revalidate even a model instance supplied by a custom adapter.
                draft = MetricDraft.model_validate(raw.model_dump())
            except Exception:
                raise ProfileUpdateError(
                    "Metric synthesis failed; no updated profile was returned."
                ) from None

            metric = previous.model_dump() if previous else {}
            metric.update(draft.model_dump())
            metric["evidence_ids"] = list(
                dict.fromkeys([*old_ids, *(card.card_id for card in fresh)])
            )
            result.metrics[key] = ProfileMetric.model_validate(metric)
        return result
