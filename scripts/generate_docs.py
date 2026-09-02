"""
Generate ``docs/ONTOLOGY.md`` - the entity/relationship reference - directly
from the models, so the documentation cannot drift from the code.

Run:  python3 generate_docs.py
"""

from __future__ import annotations

import inspect
import typing
from pathlib import Path

import src.app.graph.schema as M

OUT = Path(__file__).resolve().parent.parent / "docs" / "data" / "ONTOLOGY.md"

GROUPS: list[tuple[str, list[str], str]] = [
    (
        "Organisational scope",
        ["Cohort", "Round", "Group"],
        "The containers employer authorisation is scoped against (FR-05).",
    ),
    (
        "Identity",
        ["Learner", "LearnerIdentity"],
        "One canonical person, plus every source identity that resolves to them.",
    ),
    (
        "Skills",
        ["Skill"],
        "The canonical skill registry; aliases collapse surface forms onto one node.",
    ),
    (
        "Work and learning",
        [
            "Project",
            "Task",
            "LearningExperience",
            "Attempt",
            "Submission",
            "Artifact",
        ],
        "What was assigned, what was handed in, and the files inside it.",
    ),
    (
        "Assessment",
        ["Rubric", "RubricCriterion", "Assessment"],
        "How work was graded, down to the individual rubric point.",
    ),
    (
        "Meetings and interactions",
        ["Meeting", "Interaction"],
        "Where behavioural signal comes from.",
    ),
    (
        "Evidence",
        ["Evidence"],
        "The centre of the ontology: atomic, citable, provenance-carrying proof.",
    ),
    (
        "Derived state",
        ["SkillAssertion", "Observation"],
        "Computed opinions. Versioned, recomputable, never overwriting source truth.",
    ),
    (
        "Career goal and closed loop",
        ["CareerGoal", "Scenario", "Recommendation"],
        "Sprint 4 surface. CareerGoal is P0 now; Scenario/Recommendation are stubs.",
    ),
    (
        "Employer access",
        ["Employer", "AccessGrant"],
        "Deny-by-default authorisation. Enforced in Sprint 2; fields exist now.",
    ),
]


def type_name(annotation: object) -> str:
    """Render a field annotation as short, readable Markdown."""
    import enum
    import types as _types
    from datetime import datetime as _dt

    def render(a: object) -> str:
        if a is type(None):
            return "None"
        # Every datetime in this ontology is a UtcDatetime; Pydantic flattens the
        # Annotated wrapper away on required fields, so label the bare type too.
        if a is _dt:
            return "datetime (UTC)"
        # Annotated[...] - unwrap, but name our two semantic aliases.
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
            if issubclass(a, enum.Enum):
                return a.__name__
            return a.__name__
        text = str(a).replace("typing.", "").replace("learner_graph_models.", "")
        return text[:44]

    out = render(annotation)
    if len(out) > 48:
        out = out[:45] + "..."
    # Escape pipes so unions do not break the Markdown table.
    return "`" + out.replace("|", "\\|") + "`"


def node_kind(cls: type) -> str:
    if issubclass(cls, M.DerivedNode):
        return "derived"
    if issubclass(cls, M.SourceNode):
        return "source"
    return "registry"


def node_table(label: str) -> list[str]:
    cls = M.NODE_CLASSES[label]
    lines = [f"#### `{label}`  ({node_kind(cls)})", ""]
    doc = inspect.getdoc(cls)
    if doc:
        lines += [doc.strip(), ""]
    lines += ["| property | type | required | notes |", "|---|---|---|---|"]
    for name, field in cls.model_fields.items():
        if name == "label":
            continue
        note = (field.description or "").replace("\n", " ").strip()
        if len(note) > 90:
            note = note[:87] + "..."
        lines.append(
            f"| `{name}` | {type_name(field.annotation)} | "
            f"{'yes' if field.is_required() else 'no'} | {note} |"
        )
    lines.append("")
    return lines


def build() -> str:
    L: list[str] = [
        "# Professional Learner Graph - Ontology Reference",
        "",
        f"- ontology version: `{M.ONTOLOGY_VERSION}`",
        f"- schema version: `{M.SCHEMA_VERSION}`",
        f"- node labels: **{len(M.NODE_CLASSES)}**",
        f"- relationship types: **{len(list(M.EdgeType))}** "
        f"across **{len(M.EDGE_SPECS)}** legal endpoint pairs",
        "",
        "> **Generated file.** Produced by `generate_docs.py` from",
        "> `learner_graph_models.py`. Edit the models and regenerate.",
        "",
        "Node kinds:",
        "",
        "| kind | meaning | carries |",
        "|---|---|---|",
        "| `source` | mirrors a record that exists in a source system | `provenance` "
        "(required) |",
        "| `derived` | a computed opinion the platform produced | `computed_at`, "
        "`computed_by` |",
        "| `registry` | a taxonomy entry owned by the platform | neither |",
        "",
        "---",
        "",
        "## 1. Node types",
        "",
    ]

    for title, labels, blurb in GROUPS:
        L += [f"### {title}", "", blurb, ""]
        for label in labels:
            L += node_table(label)
        L.append("---")
        L.append("")

    # ---- relationships ----
    L += [
        "## 2. Relationships",
        "",
        "Every relationship below is registered in `EDGE_SPECS`. An edge whose",
        "`(type, source, target)` triple is not in this table is **rejected at",
        "validation time** - this is what stops the ingestion, identity and API",
        "workstreams from inventing divergent edges.",
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
        "| relationship | cardinality | properties | meaning |",
        "|---|---|---|---|",
    ]
    for spec in sorted(M.EDGE_SPECS, key=lambda s: (s.type.value, s.source_label)):
        props = f"`{spec.property_model}`" if spec.property_model else "-"
        L.append(
            f"| `(:{spec.source_label})-[:{spec.type.value}]->(:{spec.target_label})` "
            f"| "
            f"`{spec.cardinality.value}` | {props} | {spec.description} |"
        )

    # ---- edge property payloads ----
    L += ["", "### Relationship property payloads", ""]
    for name, model in sorted(M._PROPERTY_MODELS.items()):
        L += [f"#### `{name}`", ""]
        doc = inspect.getdoc(model)
        if doc and not doc.startswith("!!"):
            L += [doc.strip(), ""]
        L += ["| property | type | required |", "|---|---|---|"]
        for fname, field in model.model_fields.items():
            L.append(
                f"| `{fname}` | {type_name(field.annotation)} | "
                f"{'yes' if field.is_required() else 'no'} |"
            )
        L.append("")

    # ---- vocabularies ----
    L += [
        "---",
        "",
        "## 3. Controlled vocabularies",
        "",
        "Values follow the source export wherever one already exists, so ingestion",
        "never has to translate between two vocabularies.",
        "",
    ]
    enums = [
        (n, o)
        for n, o in vars(M).items()
        if isinstance(o, type)
        and issubclass(o, __import__("enum").Enum)
        and o.__module__ == M.__name__
    ]
    for name, enum_cls in sorted(enums):
        doc = (inspect.getdoc(enum_cls) or "").split("\n")[0]
        doc = "" if doc.startswith("An enumeration") else doc
        L.append(f"**`{name}`**" + (f" - {doc}" if doc else ""))
        L.append("")
        L.append("  " + ", ".join(f"`{m.value}`" for m in enum_cls))
        L.append("")

    # ---- cardinality rules narrative ----
    L += [
        "---",
        "",
        "## 4. Cardinality rules that carry product meaning",
        "",
        "Most cardinalities are bookkeeping. These five are product decisions:",
        "",
        "| rule | why |",
        "|---|---|",
        "| `(:Evidence)-[:EVIDENCE_FOR_LEARNER]->(:Learner)` is `N:1` | "
        "An evidence item is about exactly one person. Shared evidence would make "
        "per-learner access scoping unenforceable. |",
        "| `(:SkillAssertion)-[:SUPPORTED_BY_EVIDENCE]->(:Evidence)` is `N:M` | "
        "One claim is backed by many evidence items, and one evidence item supports "
        "many claims. This is why Evidence is a node, not an edge property. |",
        "| `(:SkillAssertion)-[:ABOUT_SKILL]->(:Skill)` is `N:1` | "
        "An assertion concerns exactly one skill at one tier, so recomputation can "
        "target it precisely. |",
        "| `(:Learner)-[:HAS_CAREER_GOAL]->(:CareerGoal)` is `1:1` | "
        "FR-11: exactly one current goal or one explicit unknown state. Two goals "
        "would make the gap engine ambiguous. |",
        "| `(:Evidence)-[:DERIVED_FROM]->(:Artifact)` is `N:M` | "
        "One graded rubric point routinely cites several artifact chunks "
        "(`chunks_ids_met` in the real grader payload). |",
        "",
        "## 5. Invariants enforced in code",
        "",
        "`LearnerGraph` refuses to construct a graph that breaks any of these:",
        "",
        "1. every node id is unique;",
        "2. every edge endpoint exists and its declared label matches the node;",
        "3. every edge is a registered `(type, source, target)` triple;",
        "4. declared cardinality holds;",
        "5. **Evidence-First** -",
        "   every `SkillAssertion` with a status other than `no_evidence` has at least",
        "   one `SUPPORTED_BY_EVIDENCE` edge; every `Observation` has one; every",
        "   `Evidence` has a `DERIVED_FROM` source record and an "
        "`EVIDENCE_FOR_LEARNER` owner.",
        "",
        "The same five are expressed as Cypher in section 6 of",
        "`schema_constraints.cql` and asserted against a live database by",
        "`verify_neo4j.sh`.",
        "",
    ]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.name}: {len(build().splitlines())} lines")
