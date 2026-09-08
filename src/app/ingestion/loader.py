"""
Batch loader: takes a validated ``LearnerGraph`` (LearnerProfile / DataSource
/ MemoryCard nodes, plus their edges) and writes it into Neo4j.

Idempotent by construction, not by convention: every node id is a
deterministic UUIDv5 of (label, natural key) - see ``src/app/graph/ids.py`` -
and every write is a Cypher ``MERGE`` keyed on that id, so loading the same
batch twice never creates a duplicate node or relationship. Nodes are
loaded before edges, since an edge's ``MATCH`` would simply match nothing if
its endpoints didn't exist yet.

Chunking
--------
Rows are sent in chunks of ``settings.graph_loader_batch_size`` so one
statement never carries an unbounded payload. Each chunk is its own
transaction, which is what keeps memory and transaction size bounded on a
large ingestion run - the trade-off is that atomicity is per chunk, not per
whole graph. For a batch small enough to fit in one chunk (the common case,
and every case in the current dataset) the whole load is atomic.

``load_graph_atomic()`` is available when a caller needs all-or-nothing
across the entire payload and is willing to hold it in one transaction.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Iterator, Sequence

from neo4j import Driver, ManagedTransaction

from src.app.core.config import settings
from src.app.graph import queries
from src.app.graph.schema import GraphNode, LearnerGraph
from src.app.graph.serialization import flatten_node

logger = logging.getLogger(__name__)

__all__ = ["load_graph", "load_graph_atomic"]


def _chunks(rows: list[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    if size < 1:
        raise ValueError(f"batch size must be >= 1, got {size}")
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _group_nodes_by_label(
    nodes: Sequence[GraphNode],
) -> dict[str, list[dict[str, Any]]]:
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        by_label[node.label].append(flatten_node(node))
    return by_label


def _group_edges(
    graph: LearnerGraph,
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    by_rel: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in graph.edges:
        key = (edge.type.value, edge.source_label, edge.target_label)
        by_rel[key].append({"src": edge.source_id, "dst": edge.target_id})
    return by_rel


def _load_nodes(tx: ManagedTransaction, graph: LearnerGraph) -> None:
    for label, rows in _group_nodes_by_label(graph.nodes).items():
        queries.merge_nodes(tx, label, rows)


def _load_edges(tx: ManagedTransaction, graph: LearnerGraph) -> None:
    for (edge_type, source_label, target_label), rows in _group_edges(graph).items():
        queries.merge_edges(tx, edge_type, source_label, target_label, rows)


def _load_batch(tx: ManagedTransaction, graph: LearnerGraph) -> None:
    _load_nodes(tx, graph)
    _load_edges(tx, graph)


def load_graph(
    driver: Driver, graph: LearnerGraph, batch_size: int | None = None
) -> None:
    """Idempotently write ``graph`` into Neo4j, chunked.

    Nodes are written before edges so every edge finds its endpoints. Each
    chunk runs in its own write transaction: a chunk either lands in full or
    not at all, and a failure stops the run rather than continuing past it.
    """
    size = batch_size if batch_size is not None else settings.graph_loader_batch_size

    with driver.session() as session:
        for label, rows in _group_nodes_by_label(graph.nodes).items():
            for chunk in _chunks(rows, size):
                session.execute_write(queries.merge_nodes, label, chunk)
            logger.debug("merged %d %s node(s)", len(rows), label)

        for edge_key, rows in _group_edges(graph).items():
            edge_type, source_label, target_label = edge_key
            for chunk in _chunks(rows, size):
                session.execute_write(
                    queries.merge_edges, edge_type, source_label, target_label, chunk
                )
            logger.debug("merged %d %s edge(s)", len(rows), edge_type)


def load_graph_atomic(driver: Driver, graph: LearnerGraph) -> None:
    """Write the whole graph in ONE transaction - all of it commits or none
    of it does, at the cost of holding the entire payload in one transaction.

    Use this when a partially-loaded graph would be worse than no graph at
    all. For large payloads prefer ``load_graph()``.
    """
    with driver.session() as session:
        session.execute_write(_load_batch, graph)
