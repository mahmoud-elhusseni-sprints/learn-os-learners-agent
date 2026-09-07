"""
Generate ``docs/data/ONTOLOGY.md`` - the entity/relationship reference -
directly from the models, so the documentation cannot drift from the code.

Rewritten alongside the schema redesign: 3 node types instead of 26, so the
group/kind machinery the old generator needed is gone. Nothing here is
hand-maintained content; every fact is pulled from ``src/app/graph/schema.py``.

Run:  python3 scripts/generate_docs.py
"""

from __future__ import annotations

import enum
import inspect
import types as _types
import typing
from datetime import datetime as _dt
from pathlib import Path

import src.app.graph.schema as M

OUT = Path(__file__).resolve().parent.parent / "docs" / "data" / "ONTOLOGY.md"


def type_name(annotation: object) -> str:
    """Render a field annotation as short, readable Markdown."""

    def render(a: object) -> str:
        if a is type(None):
            return "None"
        if a is _dt:
            return "datetime (UTC)"
        if hasattr(a, "__metadata__"):
            base = a.__origin__  # type: ignore[attr-defined]
            if base is _dt:
                return "datetime (UTC)"
            if base is float:
                return "float 0..1"
            return render(base)
        origin = typing.get_origin(a)
        if origin in (typing.Union, _types.UnionType):
            args = typing.get_args(a)
            inner = [x for x in args if x is not type(None)]
            text = " | ".join(render(x) for x in inner)
            return f"{text} | None" if type(None) in args else text
        if origin in (list, set, frozenset, tuple):
            inner = ", ".join(render(x) for x in typing.get_args(a))
            return f"{origin.__name__}[{inner}]"
        if origin is dict:
            k, v = typing.get_args(a)
            return f"dict[{render(k)}, {render(v)}]"
        if isinstance(a, type):
            return a.__name__
        return str(a).replace("typing.", "")[:44]

    out = render(annotation)
    if len(out) > 48:
        out = out[:45] + "..."
    return "`" + out.replace("|", "\\|") + "`"


def model_table(cls: type, *, skip: tuple[str, ...] = ()) -> list[str]:
    lines = ["| property | type | required | notes |", "|---|---|---|---|"]
    for name, field in cls.model_fields.items():
        if name in skip:
            continue
        note = (field.description or "").replace("\n", " ").strip()
        if len(note) > 100:
            note = note[:97] + "..."
        lines.append(
            f"| `{name}` | {type_name(field.annotation)} | "
            f"{'yes' if field.is_required() else 'no'} | {note} |"
        )
    lines.append("")
    return lines


def node_section(label: str) -> list[str]:
    cls = M.NODE_CLASSES[label]
    lines = [f"### `{label}`", ""]
    doc = inspect.getdoc(cls)
    if doc:
        lines += [doc.strip(), ""]
    lines += model_table(cls, skip=("label",))
    return lines


def payload_section(name: str, model: type) -> list[str]:
    lines = [f"#### `{name}`", ""]
    doc = inspect.getdoc(model)
    if doc:
        lines += [doc.strip(), ""]
    lines += model_table(model)
    return lines


def build() -> str:
    L: list[str] = [
        "# Professional Learner Graph - Ontology Reference",
        "",
        f"- ontology version: `{M.ONTOLOGY_VERSION}`",
        f"- schema version: `{M.SCHEMA_VERSION}`",
        f"- node labels: **{len(M.NODE_CLASSES)}** "
        f"({', '.join(sorted(M.NODE_CLASSES))})",
        f"- relationship types: **{len(list(M.EdgeType))}** "
        f"across **{len(M.EDGE_SPECS)}** legal endpoint pairs",
        "",
        "> **Generated file.** Produced by `scripts/generate_docs.py` from",
        "> `src/app/graph/schema.py`. Edit the models and regenerate; do not",
        "> hand-edit this file.",
        "",
        "This is the v2, minimal ontology: 3 node types "
        "(`LearnerProfile`, `DataSource`, `MemoryCard`), rewritten from a "
        "26-node design per the mentor's rejection of the previous schema "
        "and the architecture specified in the mentor-authored MD file. "
        "See the module docstring in `src/app/graph/schema.py` for the full "
        "before/after rationale, including what was removed and why.",
        "",
        "---",
        "",
        "## 1. Node types",
        "",
    ]

    for label in sorted(M.NODE_CLASSES):
        L += node_section(label)
        L.append("---")
        L.append("")

    L += [
        "## 2. Embedded payload shapes",
        "",
        "`DataSource.payload` is a discriminated union, chosen by "
        "`datasource_name` - never a separate node.",
        "",
    ]
    for name, model in [
        ("ReviewPayload", M.ReviewPayload),
        ("RubricPointEvaluation", M.RubricPointEvaluation),
        ("AssessmentPayload", M.AssessmentPayload),
        ("AssessmentAnswerItem", M.AssessmentAnswerItem),
        ("StubPayload", M.StubPayload),
    ]:
        L += payload_section(name, model)

    L += [
        "---",
        "",
        "## 3. Relationships",
        "",
        "Every relationship below is registered in `EDGE_SPECS`. An edge "
        "whose `(type, source, target)` triple is not in this table is "
        "**rejected at validation time**.",
        "",
        "Cardinality is read left-to-right:",
        "",
        "| notation | meaning |",
        "|---|---|",
        "| `1:1` | each source has at most one target, and vice versa |",
        "| `1:N` | one source, many targets; each target has one source |",
        "| `N:1` | many sources, one target; each source has one target |",
        "| `N:M` | unconstrained both ways |",
        "",
        "| relationship | cardinality | meaning |",
        "|---|---|---|",
    ]
    for spec in sorted(M.EDGE_SPECS, key=lambda s: (s.type.value, s.source_label)):
        L.append(
            f"| `(:{spec.source_label})-[:{spec.type.value}]->(:{spec.target_label})` "
            f"| `{spec.cardinality.value}` | {spec.description} |"
        )

    L += [
        "",
        "---",
        "",
        "## 4. Controlled vocabularies",
        "",
        "Values follow the source export wherever one already exists "
        "(including its misspellings, e.g. `assesments`), so ingestion "
        "never has to translate between two vocabularies.",
        "",
    ]
    enums = [
        (n, o)
        for n, o in vars(M).items()
        if isinstance(o, type)
        and issubclass(o, enum.Enum)
        and o.__module__ == M.__name__
    ]
    for name, enum_cls in sorted(enums):
        doc = (inspect.getdoc(enum_cls) or "").split("\n")[0]
        doc = "" if doc.startswith("An enumeration") else doc
        L.append(f"**`{name}`**" + (f" - {doc}" if doc else ""))
        L.append("")
        L.append("  " + ", ".join(f"`{m.value}`" for m in enum_cls))
        L.append("")

    L += [
        "---",
        "",
        "## 5. Invariants enforced in code",
        "",
        "`LearnerGraph` refuses to construct a graph that breaks any of these:",
        "",
        "1. every node id is unique;",
        "2. every edge endpoint exists and its declared label matches the node;",
        "3. every edge is a registered `(type, source, target)` triple;",
        "4. declared cardinality holds;",
        "5. `DataSource.payload`'s concrete type matches its `datasource_name` "
        "(`_payload_matches_datasource_name`);",
        "6. an `assesments` payload's `score` never exceeds its `max_score` "
        "(`_score_within_max`).",
        "",
        'There is **no** "Evidence-First" invariant in this version - the '
        "previous design's Evidence/SkillAssertion nodes do not exist here, "
        "so there is nothing analogous to enforce. A `DataSource`'s payload "
        "is trusted as delivered. See the schema module docstring for why "
        "this is a deliberate, flagged loss of guarantee rather than an "
        "oversight.",
        "",
        "The same rules are expressed as Cypher constraints/indexes in "
        "`docs/data/schema_constraints.cql`.",
        "",
    ]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = build()
    OUT.write_text(text, encoding="utf-8")
    rel = OUT.relative_to(OUT.parent.parent.parent)
    print(f"wrote {rel}: {len(text.splitlines())} lines")
