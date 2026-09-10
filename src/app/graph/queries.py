"""
Reusable, parameterized Cypher for writing graph data.

Every value that comes from data (ids, properties) is passed as a query
parameter, never interpolated into the query string - that's what keeps
this safe from injection. The one thing that genuinely cannot be a
parameter is a node label or relationship type: Cypher has no syntax for
parameterizing those, in any driver, for any database. The labels and
types used here always come from a closed, validated set - ``NODE_CLASSES``
and ``EdgeType`` in ``src/app/graph/schema.py`` - never from raw input, so
interpolating them is the correct approach, not a shortcut around it.
"""

from __future__ import annotations

from typing import Any

from neo4j import ManagedTransaction


def merge_nodes(tx: ManagedTransaction, label: str, rows: list[dict[str, Any]]) -> None:
    """UNWIND + MERGE one batch of same-label nodes, keyed by ``id``.

    ``.consume()`` discards the (empty) result and returns the summary. It
    isn't needed for correctness on the current driver - a failing statement
    already raises at the ``run()`` call - but it makes that independent of
    the driver's result-streaming behaviour rather than relying on it.
    """
    if not rows:
        return
    tx.run(
        f"UNWIND $rows AS row " f"MERGE (n:{label} {{id: row.id}}) " f"SET n += row",
        rows=rows,
    ).consume()


def merge_edges(
    tx: ManagedTransaction,
    edge_type: str,
    source_label: str,
    target_label: str,
    rows: list[dict[str, Any]],
) -> None:
    """UNWIND + MERGE one batch of same-type edges between two known labels.

    Each row is ``{"src": <source id>, "dst": <target id>}``. MATCH (not
    MERGE) on the endpoints: an edge whose endpoints don't already exist is
    a data-ordering bug upstream, not something to silently paper over by
    creating placeholder nodes.
    """
    if not rows:
        return
    tx.run(
        f"UNWIND $rows AS row "
        f"MATCH (a:{source_label} {{id: row.src}}) "
        f"MATCH (b:{target_label} {{id: row.dst}}) "
        f"MERGE (a)-[r:{edge_type}]->(b)",
        rows=rows,
    ).consume()
