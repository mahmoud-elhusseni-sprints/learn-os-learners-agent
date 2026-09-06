"""
Deterministic identifier strategy for the Professional Learner Graph.

Why this module exists
----------------------
Sprint 1 acceptance requires that "backfill can be rerun without duplicating
events".  That property is won or lost entirely on how node identifiers are
minted.

A random UUID4 satisfies "UUIDs are unique" literally, but it breaks
re-ingestion: running the backfill twice produces two different UUIDs for the
same underlying source record, and therefore two nodes.

Instead every node id in this graph is a **UUIDv5** derived from the tuple

    (source_system, source_type, source_id)

UUIDv5 is a SHA-1 hash of a namespace + a name, so the same source record always
maps to the same UUID, on every machine, forever.  Combined with Neo4j `MERGE`
and the uniqueness constraints in ``schema_constraints.cql``, re-ingestion
becomes naturally idempotent.

Derived nodes (SkillAssertion, Observation, Evidence) are minted the same way
from a stable logical key, so recomputing a learner's profile updates the
existing node instead of accumulating duplicates.
"""

from __future__ import annotations

import uuid
from typing import Iterable

__all__ = [
    "SPRINTS_GRAPH_NAMESPACE",
    "deterministic_id",
    "composite_key",
    "learner_uid",
    "skill_uid",
    "evidence_uid",
    "assertion_uid",
    "observation_uid",
]

# Fixed, documented namespace.  Derived from the DNS name of the graph service
# so that anyone can recompute and verify it without needing a magic constant.
#   uuid.uuid5(uuid.NAMESPACE_DNS, "graph.sprints.ai")
#     -> the value asserted in test_learner_graph.py
SPRINTS_GRAPH_NAMESPACE: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "graph.sprints.ai")


def composite_key(*parts: object) -> str:
    """Build the canonical string that gets hashed into a UUIDv5.

    Parts are lower-cased and joined with ``|``.  ``None`` becomes the empty
    string so that a missing optional discriminator does not silently shift the
    key.  Using an explicit separator avoids the classic collision where
    ``("ab", "c")`` and ``("a", "bc")`` hash identically.
    """
    return "|".join("" if p is None else str(p).strip().lower() for p in parts)


def deterministic_id(
    source_system: object, source_type: object, source_id: object, *extra: object
) -> uuid.UUID:
    """Mint the stable UUIDv5 for one source record.

    >>> a = deterministic_id("virtual_internship", "learner", "900353f6")
    >>> b = deterministic_id("virtual_internship", "learner", "900353f6")
    >>> a == b
    True
    """
    return uuid.uuid5(
        SPRINTS_GRAPH_NAMESPACE,
        composite_key(source_system, source_type, source_id, *extra),
    )


# --------------------------------------------------------------------------
# Convenience wrappers.  These exist so ingestion code (Task 3) and the
# identity resolver (Task 4) mint ids the same way without re-deriving the
# convention each time.
# --------------------------------------------------------------------------


def learner_uid(source_system: object, source_learner_id: object) -> uuid.UUID:
    """Id of the *canonical* Learner node.

    Note: identity resolution (Task 4) may later decide that two source
    identities are the same person.  The merge is recorded on LearnerIdentity
    nodes; this function only mints the id used before/without a merge.
    """
    return deterministic_id(source_system, "learner", source_learner_id)


def skill_uid(canonical_name: str) -> uuid.UUID:
    """Skills are keyed by canonical name, not by a source id.

    The same skill arrives from many systems ("Python 3.11" in a task's
    technologies list, "python" in a rubric scope).  Normalisation to a
    canonical name happens before this call; aliases live on the Skill node.
    """
    return deterministic_id("canonical", "skill", canonical_name)


def evidence_uid(
    source_system: object,
    source_type: object,
    source_id: object,
    *discriminators: object,
) -> uuid.UUID:
    """Id of an Evidence node.

    ``discriminators`` distinguish several evidence items extracted from the
    same source record - e.g. one grader call yields one Evidence per rubric
    point, so the rubric point id is passed as a discriminator.
    """
    return deterministic_id(
        source_system, f"evidence:{source_type}", source_id, *discriminators
    )


def assertion_uid(
    learner_id: uuid.UUID, skill_id: uuid.UUID, tier: object
) -> uuid.UUID:
    """Id of a derived SkillAssertion.

    Keyed by (learner, skill, tier) so recomputation overwrites in place and a
    learner has at most one assertion per skill per evidence tier.
    """
    return deterministic_id(
        "derived", "skill_assertion", composite_key(learner_id, skill_id, tier)
    )


def observation_uid(
    learner_id: uuid.UUID,
    source_system: object,
    source_id: object,
    locator: object = None,
) -> uuid.UUID:
    """Id of a derived behavioural Observation."""
    return deterministic_id(
        "derived",
        "observation",
        composite_key(learner_id, source_system, source_id, locator),
    )


def all_unique(ids: Iterable[uuid.UUID]) -> bool:
    """Small helper used by validation to assert id uniqueness."""
    seen: set[uuid.UUID] = set()
    for i in ids:
        if i in seen:
            return False
        seen.add(i)
    return True
