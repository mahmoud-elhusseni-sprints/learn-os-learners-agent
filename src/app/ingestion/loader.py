"""
Batch loader: takes a validated ``LearnerGraph`` (LearnerProfile / DataSource
/ MemoryCard nodes, plus their edges) and writes it into Neo4j.

Idempotent by construction, not by convention: every node id is a
deterministic UUIDv5 of (label, natural key) - see ``src/app/graph/ids.py`` -
and every write is a Cypher ``MERGE`` keyed on that id, so loading the same
batch twice never creates a duplicate node or relationship. Nodes are
loaded before edges within the same transaction, since an edge's ``MATCH``
would simply match nothing if its endpoints didn't exist yet.

The whole batch runs as ONE write transaction (``session.execute_write``):
if anything in it raises, nothing in it is committed - a batch cannot leave
half its nodes written and none of its edges, or vice versa.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

from neo4j import Driver, ManagedTransaction

from src.app.graph import queries
from src.app.graph.schema import GraphNode, LearnerGraph
from src.app.graph.serialization import flatten_node


def _group_nodes_by_label(
    nodes: Sequence[GraphNode],
) -> dict[str, list[dict[str, Any]]]:
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        by_label[node.label].append(flatten_node(node))  # type: ignore[attr-defined]
    return by_label


def _load_nodes(tx: ManagedTransaction, graph: LearnerGraph) -> None:
    for label, rows in _group_nodes_by_label(graph.nodes).items():
        queries.merge_nodes(tx, label, rows)


def _load_edges(tx: ManagedTransaction, graph: LearnerGraph) -> None:
    by_rel: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in graph.edges:
        key = (edge.type.value, edge.source_label, edge.target_label)
        by_rel[key].append({"src": edge.source_id, "dst": edge.target_id})
    for (edge_type, source_label, target_label), rows in by_rel.items():
        queries.merge_edges(tx, edge_type, source_label, target_label, rows)


def _load_batch(tx: ManagedTransaction, graph: LearnerGraph) -> None:
    _load_nodes(tx, graph)
    _load_edges(tx, graph)


def load_graph(driver: Driver, graph: LearnerGraph) -> None:
    """Idempotently write ``graph`` into Neo4j in one write transaction."""
    with driver.session() as session:
        session.execute_write(_load_batch, graph)
