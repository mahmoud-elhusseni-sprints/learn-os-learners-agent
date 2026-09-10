# Data Schema — Ingestion Contract

The shape that cleaned data must land in before it enters the graph.

`docs/data/data.md` states that filenames and fields **must follow this
document**. This is that document.

- **Owner:** Task 2 (graph ontology)
- **Audience:** Task 4 (submissions & assessments), Task 5 (meetings & chats),
  Task 3 (batch loader)
- **Ontology version:** `0.2.0` — 3 node types, 3 relationship types
- **Full reference:** [`ONTOLOGY.md`](ONTOLOGY.md) (generated from the models)

> **This document was rewritten for the v2 ontology.** The previous version
> described a 26-node model (`Evidence`, `Provenance`, `Skill`, `Submission`,
> `Assessment`, `deterministic_id()`, `evidence_uid()`, …). The mentor
> rejected that design and it was replaced in PR #4. **None of those classes
> or helpers exist any more** — code written against the old document will
> not import. Everything below reflects what is actually in
> `src/app/graph/schema.py` today.

---

## 1. The rule

**Do not hand-roll dictionaries, and do not define your own copies of these
models.** Build objects with the models in `src/app/graph/schema.py`.

```python
# no — a typo here surfaces in Neo4j days later
row = {"learner_id": x, "verdict": y, "conf": 1.4}


# no — a parallel model means two sources of truth that silently drift
class MyLearnerProfile(BaseModel): ...


# yes — raises immediately, naming the field
from src.app.graph.schema import LearnerProfile, LearnerRole

profile = LearnerProfile(...)
```

Every node type has required fields, value ranges and a closed vocabulary.
The models enforce all three, so bad data fails in your pipeline instead of
corrupting the graph.

---

## 2. The whole model on one page

Three node types. Nothing else is a node.

```text
LearnerProfile ──PRODUCED──►  DataSource  ──EXTRACTED_INTO──► MemoryCard
      │                     (payload embedded)                     ▲
      └──────────────────── HAS_MEMORY_CARD ─────────────────────┘
```

| Relationship | Cardinality | Meaning |
| --- | --- | --- |
| `(LearnerProfile)-[:PRODUCED]->(DataSource)` | `1:N` | A learner produces many source records |
| `(DataSource)-[:EXTRACTED_INTO]->(MemoryCard)` | `1:N` | One record distils into several cards |
| `(LearnerProfile)-[:HAS_MEMORY_CARD]->(MemoryCard)` | `N:M` | Direct learner → card shortcut |

An edge whose `(type, source, target)` triple is not in that table is
**rejected at validation time**. There is no fourth node type and no fifth
relationship: if you think you need one, raise it with Task 2 first.

### Where "evidence" lives

There is **no `Evidence` node** in this model. Evidence is:

- **`DataSource.payload`** — the whole submission / mentor feedback /
  assessment record, embedded on the node as a typed object, and
- **`MemoryCard`** — the short, tagged insight distilled from it.

---

## 3. Node fields

### `LearnerProfile`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | `str` | yes | `node_id("LearnerProfile", learner_id)` — see §5 |
| `created_at` | datetime (UTC) | yes | When we wrote it down |
| `learner_id` | `str` | yes | Source system's learner id |
| `name` | `str` | yes | |
| `role` | `LearnerRole` | yes | `lead` \| `member` |
| `group_name` | `str` | yes | |
| `round_name` | `str` | yes | |
| `added_at` | datetime (UTC) | yes | When the learner joined |
| `learner_status` | `str \| None` | no | Optional; may be dropped later |

### `DataSource`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | `str` | yes | `node_id("DataSource", datasource_id)` |
| `created_at` | datetime (UTC) | yes | |
| `datasource_id` | `str` | yes | Your stable natural key — see §5 |
| `datasource_name` | `DataSourceName` | yes | `review` \| `assesments` \| `chat` \| `meetings` |
| `timestamp` | datetime (UTC) | yes | When the record happened |
| `payload` | one of the shapes below | yes | Must match `datasource_name` |

`payload` is a discriminated union, enforced by a validator:

| `datasource_name` | required payload |
| --- | --- |
| `review` | `ReviewPayload` |
| `assesments` *(sic — matches the source data)* | `AssessmentPayload` |
| `chat`, `meetings` | `StubPayload()` (empty) |

### `MemoryCard`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | `str` | yes | `node_id("MemoryCard", card_id)` |
| `created_at` | datetime (UTC) | yes | |
| `card_id` | `str` | yes | Card id from the source |
| `metric_key` | `str` | yes | e.g. `learning_goals.learner_tasks` |
| `content` | `str` | yes | The insight itself |
| `rationale` | `str \| None` | no | Why the excerpt supports it |
| `tags` | `list[str]` | no | Maps from `profile_hints` in the dataset |

---

## 4. Payload shapes

### `ReviewPayload` — submission + mentor rubric evaluation

| Field | Type | Notes |
| --- | --- | --- |
| `lx_id` | `str` | Learning-experience id |
| `task_headline` | `str` | |
| `attempt_number` | `int` | `>= 1` |
| `hours_before_deadline` | `float \| None` | Negative = late. **`None` means unknown** — do not substitute `0.0`, which means "submitted exactly at the deadline" |
| `submission_text` | `str` | |
| `assets` | `list[str]` | code repositories + media assets combined |
| `verdict` | `str` | e.g. `passed`, `failed_retry` |
| `feedback_summary` | `str` | |
| `mentor_reply` | `str` | |
| `detailed_rubric_evaluations` | `list[RubricPointEvaluation]` | |

`RubricPointEvaluation`: `rubric_id: int`, `category: str`,
`requirement: str`, `status: RubricPointStatus` (`Yes` \| `Partial` \| `No`,
capitalised — matches the grader), `evaluation_criteria: str`, `reason: str`,
`confidence_score: float` **bounded 0..1**.

### `AssessmentPayload` — LMS-style assessment

| Field | Type | Notes |
| --- | --- | --- |
| `lx_id` | `str` | |
| `assessment_type` | `str` | |
| `topic_id` | `str` | |
| `score` | `float` | `>= 0`, and **never greater than `max_score`** |
| `max_score` | `float` | `>= 0` |
| `answers` | `list[AssessmentAnswerItem]` | |

`AssessmentAnswerItem`: `question_id`, `domain`, `metric_key`,
`learner_answer`, `score` (`>= 0`), `evaluation_notes`.

### `StubPayload` — chat / meetings

Empty by design (`StubPayload()`). It rejects extra fields, so a chat record
cannot quietly accumulate review fields.

---

## 5. IDs are deterministic — never call `uuid4()`

```python
from src.app.graph.ids import node_id

nid = node_id("LearnerProfile", learner_id)  # label + natural key
```

`node_id()` is UUIDv5 over `(label, natural_key)`, lowercased and stripped,
so the same source record always yields the same id on any machine.
Combined with the loader's `MERGE`, this is what satisfies the Sprint 1
acceptance criterion *"backfill can be rerun without duplicating events."*
A random UUID4 would create a new node on every run.

Use these natural keys:

| Node | Natural key |
| --- | --- |
| `LearnerProfile` | `learner_id` from the source |
| `DataSource` | a stable composite you construct, e.g. `f"review:{learner_id}:{lx_id}:{attempt_number}"` or `f"meetings:{learner_id}:{meeting_id}"` |
| `MemoryCard` | `card_id` from the source |

The composite for `DataSource` matters: it must be stable across re-runs and
unique per record, otherwise two different reviews collapse into one node.
`scripts/build_seed.py` shows the convention in use.

---

## 6. Two normalisation rules that still bite

### 6.1 Timestamps — ISO 8601, timezone-aware, UTC

The raw export mixes formats. Both accepted forms are normalised to UTC by
the models; a naive timestamp is rejected outright.

```text
"2026-07-30T10:17:08.550Z"     accepted
"2026-07-30T10:17:08+00:00"    accepted
"2026-07-30 10:17:08"          REJECTED — no timezone
```

Pass real `datetime` objects, not strings.

### 6.2 Unknown is not zero

`hours_before_deadline=None` means "no deadline could be determined".
`0.0` means "submitted exactly on the deadline". Substituting one for the
other silently fabricates data — 18 of 32 real review records in the export
have no parseable deadline.

---

## 7. Which source file feeds which node

| Source | Produces | Notes |
| --- | --- | --- |
| `learners.jsonl` | `LearnerProfile` | `role` → `LearnerRole`; `added_at` → UTC datetime |
| `interaction_logs.jsonl` → entries tagged `grader_call` + `feedback_delivered` with a non-null `verdict` | `DataSource(review)` | `entry.submission.text` → `submission_text`, `entry.feedback.{verdict,summary,mentor_reply}`, `entry.feedback.raw` → rubric points |
| `…feedback.raw` JSON array | `RubricPointEvaluation[]` inside the payload | Array follows the `Scope Detailed Results:` marker; parse defensively and **log what you skip** |
| LMS assessments *(not in the current export)* | `DataSource(assesments)` | Nothing real populates this yet; the fixture marks its records `SYNTHETIC` |
| `meetings.jsonl` + `meeting_memory_cards.jsonl` | `DataSource(meetings)` (stub payload) | One per `(learner_id, meeting_id)` pair actually referenced by a card |
| `meeting_memory_cards.jsonl` | `MemoryCard` | `normalized_payload.content` → `content`, `.rationale` → `rationale`, `.profile_hints` → `tags` |
| chat entries | `DataSource(chat)` (stub payload) | Owned by Task 5 |

Edges to emit: `PRODUCED` for every `DataSource` you create, plus
`EXTRACTED_INTO` and `HAS_MEMORY_CARD` for every `MemoryCard`.

---

## 8. What gets rejected

| Input | Error |
| --- | --- |
| Naive timestamp | `timestamp must be timezone-aware ISO 8601` |
| Misspelled property | `Extra inputs are not permitted` |
| `confidence_score = 1.4` | `Input should be less than or equal to 1` |
| `score` above `max_score` | `score 11.0 exceeds max_score 10.0` |
| `ReviewPayload` on an `assesments` DataSource | `datasource_name='assesments' requires a AssessmentPayload payload` |
| `attempt_number = 0` | `Input should be greater than or equal to 1` |
| Reversed relationship | `illegal relationship (DataSource)-[:PRODUCED]->(LearnerProfile)` |
| Edge pointing at a node not in the batch | `dangling or mislabelled edges: …: target <id> does not exist` |
| Two nodes sharing an id | `duplicate node ids: …` |

Note what is **not** enforced any more: the old "Evidence-First" invariant
(no claim without evidence) went away with the `Evidence` / `SkillAssertion`
nodes it protected. A `DataSource` payload is trusted as delivered, so
validate your own extraction before handing it over.

---

## 9. Handing off to Task 3 (the loader)

Build a `LearnerGraph` and pass it to the loader. That's the whole handoff —
do not write Cypher yourself.

```python
from datetime import datetime, timezone

from src.app.graph.connections import get_driver
from src.app.graph.constraints import initialize_schema
from src.app.graph.schema import (
    DataSource,
    DataSourceName,
    Edge,
    EdgeType,
    LearnerGraph,
    LearnerProfile,
    LearnerRole,
    ReviewPayload,
)
from src.app.graph.ids import node_id
from src.app.ingestion.loader import load_graph

now = datetime.now(timezone.utc)

learner = LearnerProfile(
    id=node_id("LearnerProfile", row["learner_id"]),
    created_at=now,
    learner_id=row["learner_id"],
    name=row["name"],
    role=LearnerRole(row["role"]),
    group_name=row["group_name"],
    round_name=row["round_name"],
    added_at=parse_utc(row["added_at"]),
)

datasource_id = f"review:{row['learner_id']}:{lx_id}:{attempt_number}"
review = DataSource(
    id=node_id("DataSource", datasource_id),
    created_at=now,
    datasource_id=datasource_id,
    datasource_name=DataSourceName.REVIEW,
    timestamp=parse_utc(entry["ts"]),
    payload=ReviewPayload(...),
)

graph = LearnerGraph(
    generated_at=now,
    nodes=[learner, review],
    edges=[
        Edge(
            type=EdgeType.PRODUCED,
            source_label="LearnerProfile",
            source_id=learner.id,
            target_label="DataSource",
            target_id=review.id,
        )
    ],
)

driver = get_driver()
initialize_schema(driver)  # idempotent
load_graph(driver, graph)  # idempotent, one transaction
```

`LearnerGraph` validates the whole batch before a single write happens:
unique ids, every edge endpoint present and correctly labelled, every edge a
registered triple, cardinality respected.

`load_graph()` batches by label and edge type (`UNWIND` + `MERGE`) and runs
nodes and edges **in one write transaction** — a failure partway through
commits nothing.

If you need the flat property map yourself (rarely), use
`flatten_node(node)` from `src/app/graph/serialization.py`; nested payloads
are JSON-stringified onto `payload_json`, since Neo4j cannot store nested
objects.

---

## 10. Known problems in the raw export

| Count | Problem | Handling |
| --- | --- | --- |
| 246 | Real GitHub handle `MoHatemTC` survived anonymisation in `interaction_logs.jsonl` | Already scrubbed in the committed copy; **scrub again in the pipeline** if you read the original export |
| 18 / 32 | Review records with no parseable deadline | Leave `hours_before_deadline=None`; do not fill in `0.0` |
| — | Grader `feedback.raw` mixes JSON arrays with trailing prose | Parse defensively; log and count what you skip so data loss is visible |
| — | LMS assessments absent from the export | `DataSource(assesments)` has no real source yet; mark anything you generate as synthetic |
| — | Two timestamp formats in one corpus | Normalised to UTC by the models |
| — | Transcripts are Egyptian Arabic + English | Test extraction on Arabic before assuming an English pipeline works |

---

## 11. Verify your output

```bash
docker compose run --rm api python scripts/validate_seed.py   # 27 checks
docker compose run --rm api pytest                            # full suite

# against a live database
docker compose up -d neo4j
docker compose run --rm api pytest tests/test_neo4j_loader.py
```

`scripts/build_seed.py` reads the real export and produces a validated
`LearnerGraph` (7 learners, 55 DataSource records, 53 MemoryCards). It is a
**fixture generator, not the production pipeline** — but its parsing of the
grader payload, memory cards and attempt lineage is correct. Copy from it.
