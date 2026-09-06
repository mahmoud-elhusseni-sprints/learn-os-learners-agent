"""
Turn a validated ``LearnerGraph`` into an idempotent Cypher load script.

Two jobs:

1. **Flatten** Pydantic nodes into Neo4j-legal properties.  Neo4j property
   values must be primitives or arrays of primitives - no nested maps - so
   ``provenance`` is flattened onto the node and free-form maps are stored as
   JSON strings.

2. **Emit MERGE**, never CREATE.  Combined with the deterministic UUIDv5 ids
   from ``learner_graph_ids`` and the uniqueness constraints in
   ``schema_constraints.cql``, running the generated script twice leaves the
   database in exactly the same state.  That is the Sprint 1 acceptance
   criterion "backfill can be rerun without duplicating events", made
   mechanical.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from .schema import Edge, GraphNode, LearnerGraph

__all__ = [
    "PROVENANCE_FIELD_MAP",
    "flatten_node",
    "cypher_literal",
    "node_merge_statement",
    "edge_merge_statement",
    "export_graph",
]

#: How ``Provenance`` sub-fields land on the node.  ``observed_at`` is renamed
#: because Evidence/Observation already own a semantic ``observed_at`` and
#: Neo4j has one flat namespace per node.
PROVENANCE_FIELD_MAP: dict[str, str] = {
    "source_system": "source_system",
    "source_id": "source_id",
    "source_type": "source_type",
    "source_locator": "source_locator",
    "source_url": "source_url",
    "observed_at": "source_observed_at",
    "ingested_at": "ingested_at",
    "extraction_method": "extraction_method",
    "extractor_version": "extractor_version",
}

#: Free-form maps that must be serialised rather than stored as properties.
_JSON_STRING_FIELDS = {"sensitive_attributes"}


def flatten_node(node: GraphNode) -> dict[str, Any]:
    """Flatten one node into Neo4j-legal ``{property: value}``."""
    raw = node.model_dump(mode="json", exclude_none=True)
    raw.pop("label", None)

    flat: dict[str, Any] = {}
    for key, value in raw.items():
        if key == "provenance":
            for sub, target in PROVENANCE_FIELD_MAP.items():
                if sub in value and value[sub] is not None:
                    flat[target] = value[sub]
        elif key in _JSON_STRING_FIELDS:
            if value:
                flat[f"{key}_json"] = json.dumps(
                    value, sort_keys=True, ensure_ascii=False
                )
        elif isinstance(value, dict):
            flat[f"{key}_json"] = json.dumps(value, sort_keys=True, ensure_ascii=False)
        else:
            flat[key] = value
    return flat


# --------------------------------------------------------------------------
# Cypher literal rendering
# --------------------------------------------------------------------------

_ISO_HINT = ("T", ":")


def _looks_like_timestamp(key: str, value: str) -> bool:
    return (
        key.endswith("_at") or key.endswith("_utc") or key.endswith("_date")
    ) and all(h in value for h in _ISO_HINT)


def cypher_literal(value: Any, key: str = "") -> str:
    """Render a Python value as a Cypher literal.

    Timestamp-looking strings on timestamp-looking keys become
    ``datetime('...')`` so Neo4j stores a real temporal type and range
    indexes on dates actually work.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, Enum):
        return cypher_literal(value.value, key)
    if isinstance(value, UUID):
        return _quote(str(value))
    if isinstance(value, datetime):
        return f"datetime('{value.isoformat()}')"
    if isinstance(value, str):
        if _looks_like_timestamp(key, value):
            return f"datetime('{value}')"
        return _quote(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(cypher_literal(v) for v in value) + "]"
    raise TypeError(
        f"cannot render {type(value).__name__} as a Cypher literal (key={key!r})"
    )


def _quote(s: str) -> str:
    escaped = (
        s.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f"'{escaped}'"


def _prop_map(props: dict[str, Any], indent: str = "  ") -> str:
    if not props:
        return "{}"
    items = [f"{indent}  {k}: {cypher_literal(v, k)}" for k, v in sorted(props.items())]
    return "{\n" + ",\n".join(items) + f"\n{indent}}}"


# --------------------------------------------------------------------------
# Statement builders
# --------------------------------------------------------------------------


def node_merge_statement(node: GraphNode) -> str:
    props = flatten_node(node)
    node_id = props.pop("id")
    label = node.label  # type: ignore[attr-defined]
    return (
        f"MERGE (n:{label} {{id: {cypher_literal(node_id, 'id')}}})\n"
        f"SET n += {_prop_map(props)};"
    )


def edge_merge_statement(edge: Edge) -> str:
    src = cypher_literal(edge.source_id, "id")
    dst = cypher_literal(edge.target_id, "id")
    head = (
        f"MATCH (a:{edge.source_label} {{id: {src}}})\n"
        f"MATCH (b:{edge.target_label} {{id: {dst}}})\n"
        f"MERGE (a)-[r:{edge.type.value}]->(b)"
    )
    if edge.properties:
        return head + f"\nSET r += {_prop_map(edge.properties)};"
    return head + ";"


def export_graph(graph: LearnerGraph, *, title: str = "Learner graph seed") -> str:
    """Render the whole graph as one re-runnable Cypher script."""
    lines: list[str] = [
        "// " + "=" * 74,
        f"// {title}",
        f"// generated from schema {graph.schema_version} (ontology "
        f"{graph.ontology_version})",
        f"// generated_at: {graph.generated_at.isoformat()}",
        "//",
        "// Idempotent by construction: every id is a deterministic UUIDv5 and every",
        "// write is a MERGE, so running this file twice is a no-op the second time.",
        "// Apply schema_constraints.cql BEFORE this file.",
        "// " + "=" * 74,
        "",
        "// ---------------------------------------------------------------------",
        f"// Nodes ({len(graph.nodes)})",
        "// ---------------------------------------------------------------------",
        "",
    ]

    for label in sorted({n.label for n in graph.nodes}):
        group = [n for n in graph.nodes if n.label == label]
        lines.append(f"// --- {label} ({len(group)}) ---")
        for node in group:
            lines.append(node_merge_statement(node))
            lines.append("")

    lines += [
        "// ---------------------------------------------------------------------",
        f"// Relationships ({len(graph.edges)})",
        "// ---------------------------------------------------------------------",
        "",
    ]
    for edge_type in sorted({e.type.value for e in graph.edges}):
        edge_group = [e for e in graph.edges if e.type.value == edge_type]
        lines.append(f"// --- {edge_type} ({len(edge_group)}) ---")
        for edge in edge_group:
            lines.append(edge_merge_statement(edge))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def required_neo4j_properties(node_cls: type[GraphNode]) -> list[str]:
    """Flattened property names that are structurally required for a label.

    Derived from the Pydantic models themselves, so the existence constraints
    in ``schema_constraints.cql`` cannot drift away from the Python contract.
    """
    required: list[str] = []
    for name, field in node_cls.model_fields.items():
        if name == "label" or not field.is_required():
            continue
        if name == "provenance":
            from .schema import Provenance

            for sub, sub_field in Provenance.model_fields.items():
                if sub_field.is_required():
                    required.append(PROVENANCE_FIELD_MAP[sub])
        else:
            required.append(name)
    return sorted(set(required))
