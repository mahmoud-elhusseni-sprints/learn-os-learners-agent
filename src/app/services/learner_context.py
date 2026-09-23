"""Resolve explicit graph identities, never infer a saved identity from answers."""

import re
from dataclasses import dataclass
from typing import Iterable

from src.app.graph.connections import get_driver


def learner_directory() -> list[dict[str, str]]:
    """Read identity metadata only. Storage errors must not look like no matches."""
    with get_driver().session() as session:
        return [
            dict(row)
            for row in session.run(
                "MATCH (l:LearnerProfile) "
                "RETURN l.learner_id AS learner_id, l.name AS name"
            )
        ]


@dataclass(frozen=True)
class LearnerContext:
    active: str | None
    saved: str | None
    clarification: str | None = None
    preserve_default: bool = False


def resolve_context(
    message: str,
    saved: str | None,
    learners: Iterable[dict[str, str]],
) -> LearnerContext:
    """Full names/IDs override defaults; multi-name turns never overwrite them.

    Match whole, case-insensitive identities, with longest overlapping names
    taking precedence. Duplicate names require clarification, not LIMIT 1.
    Partial names and unrecognized aliases are left to clarification/tool lookup;
    they are never guessed and persisted by this resolver.
    """
    matches: list[tuple[int, int, str]] = []
    for learner in learners:
        identity = learner.get("learner_id")
        if not identity:
            continue
        for alias in {identity, learner.get("name") or ""} - {""}:
            for match in re.finditer(
                r"(?<!\w)" + re.escape(alias) + r"(?!\w)", message, re.I
            ):
                matches.append((match.start(), match.end(), identity))
    matches = [
        item
        for item in matches
        if not any(
            other[0] <= item[0]
            and other[1] >= item[1]
            and other[1] - other[0] > item[1] - item[0]
            for other in matches
        )
    ]
    spans: dict[tuple[int, int], set[str]] = {}
    for start, end, identity in matches:
        spans.setdefault((start, end), set()).add(identity)
    if any(len(ids) > 1 for ids in spans.values()):
        return LearnerContext(
            None, saved, "Which learner do you mean? Please provide their ID.", True
        )
    ids = {identity for _, _, identity in matches}
    comparison = bool(
        re.search(r"\b(compare|comparison|versus|vs)\b|قارن|مقارنة", message, re.I)
    )
    if len(ids) > 1:
        return LearnerContext(None, saved, preserve_default=True)
    if comparison:
        return LearnerContext(saved, saved, preserve_default=True)
    if len(ids) == 1:
        identity = next(iter(ids))
        return LearnerContext(identity, identity)
    if saved is None and re.search(r"\b(his|her|their|he|she|him)\b", message, re.I):
        return LearnerContext(
            None, None, "Which learner do you mean? Please provide a name or ID."
        )
    return LearnerContext(saved, saved)
