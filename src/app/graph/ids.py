"""
Deterministic identifiers for the (v2, minimal) Professional Learner Graph.

Simplified from v1 alongside the schema rewrite: with only three node types,
one generic function keyed on (label, natural_key) replaces the previous
per-node-type helpers (learner_uid, skill_uid, evidence_uid, ...).

Why deterministic ids still matter, unchanged from v1
------------------------------------------------------
A random id would satisfy "ids are unique" literally while breaking
re-ingestion: running the load twice would mint a second id for the same
source record and duplicate the node. UUIDv5 hashes the node's own natural
key, so the same record always produces the same id, on any machine,
forever. Combined with a MERGE-based loader, re-ingestion becomes
idempotent. Nothing in the schema rewrite changes this requirement - it is
a database-integrity property, not part of the ontology the mentor's MD
file is describing.
"""

from __future__ import annotations

import uuid

__all__ = ["SPRINTS_GRAPH_NAMESPACE", "node_id"]

SPRINTS_GRAPH_NAMESPACE: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "graph.sprints.ai")


def node_id(label: str, natural_key: str) -> str:
    """Deterministic id for one node.

    >>> node_id("LearnerProfile", "127c834c-f7ce-4cc7-9a73-c8f93c8648aa") == \
        node_id("LearnerProfile", "127c834c-f7ce-4cc7-9a73-c8f93c8648aa")
    True
    """
    key = f"{label.strip().lower()}|{str(natural_key).strip().lower()}"
    return str(uuid.uuid5(SPRINTS_GRAPH_NAMESPACE, key))
