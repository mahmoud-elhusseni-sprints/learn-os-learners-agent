"""
Turn a validated ``LearnerGraph`` (v2, minimal) into Neo4j-legal properties
and an idempotent Cypher load script.

Simplified alongside the schema rewrite. The one thing that still needs
real thought: Neo4j properties must be primitives or arrays of primitives -
no nested objects - but ``DataSource.payload`` is a nested Pydantic model
(``ReviewPayload`` / ``AssessmentPayload`` / ``StubPayload``). It is
JSON-stringified onto the node as ``payload_json``, the same pattern v1
used for ``Learner.sensitive_attributes``.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from src.app.graph.schema import Edge, GraphNode, LearnerGraph

__all__ = [
    "flatten_node",
    "cypher_literal",
    "node_merge_statement",
    "edge_merge_statement",
    "export_graph",
]


def flatten_node(node: GraphNode) -> dict[str, Any]:
    """Flatten one node into Neo4j-legal ``{property: value}``.

    Any field that is a nested model or dict (currently only
    ``DataSource.payload``) is serialised to a JSON string under
    ``<field>_json``, since Neo4j cannot store nested structures.
    """
    raw = node.model_dump(mode="json", exclude_none=True)
    raw.pop("label", None)

    flat: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            flat[f"{key}_json"] = json.dumps(value, sort_keys=True, ensure_ascii=False)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            # a list of nested objects (e.g. tags is a list[str] and stays
            # as-is; this branch only catches a list of dicts, which does
            # not currently occur but is guarded rather than silently
            # mis-stored if the schema grows one)
            flat[f"{key}_json"] = json.dumps(value, sort_keys=True, ensure_ascii=False)
        else:
            flat[key] = value
    return flat


_ISO_HINT = ("T", ":")


def _looks_like_timestamp(key: str, value: str) -> bool:
    return (key.endswith("_at") or key.endswith("_utc") or key == "timestamp") and all(
        h in value for h in _ISO_HINT
    )


def cypher_literal(value: Any, key: str = "") -> str:
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


def node_merge_statement(node: GraphNode) -> str:
    props = flatten_node(node)
    node_id = props.pop("id")
    label = node.label
    return (
        f"MERGE (n:{label} {{id: {cypher_literal(node_id, 'id')}}})\n"
        f"SET n += {_prop_map(props)};"
    )


def edge_merge_statement(edge: Edge) -> str:
    src = cypher_literal(edge.source_id, "id")
    dst = cypher_literal(edge.target_id, "id")
    return (
        f"MATCH (a:{edge.source_label} {{id: {src}}})\n"
        f"MATCH (b:{edge.target_label} {{id: {dst}}})\n"
        f"MERGE (a)-[r:{edge.type.value}]->(b);"
    )


def export_graph(graph: LearnerGraph, *, title: str = "Learner graph seed") -> str:
    lines: list[str] = [
        "// " + "=" * 74,
        f"// {title}",
        f"// generated from schema {graph.schema_version} "
        f"(ontology {graph.ontology_version})",
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
