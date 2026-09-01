# Data Schema — Ingestion Contract

The shape that cleaned data must land in before it enters the graph.

`docs/data/data.md` states that filenames and fields **must follow this
document**. This is that document.

- **Owner:** Task 2 (graph ontology)
- **Audience:** Task 4 (submissions & assessments), Task 5 (meetings & chats),
  Task 3 (batch loader)
- **Ontology version:** `0.1.0` — 25 node types, 42 relationship types
- **Full reference:** [`ONTOLOGY.md`](ONTOLOGY.md)

---

## 1. The rule

**Do not hand-roll dictionaries.** Build objects with the models in
`src/app/graph/schema.py`.

```python
# no — a typo here surfaces in Neo4j days later
row = {"learner_id": x, "skill": y, "conf": 1.4}

# yes — raises immediately, naming the field
from src.app.graph.schema import Evidence, Provenance
ev = Evidence(...)
```

Every node type has required fields, value ranges and a closed vocabulary. The
models enforce all three, so bad data fails in your pipeline instead of
corrupting the graph.

---

## 2. Five normalisation rules

### 2.1 Timestamps — ISO 8601, timezone-aware, UTC

The raw export mixes two formats: **874** records use `Z`, **159** use
`+00:00`. `meetings.jsonl` also carries a `starts_at_local` that is not UTC.

```text
"2026-07-21T20:33:14.676Z"     accepted
"2026-07-21T20:33:14+00:00"    accepted
"2026-07-21 20:33:14"          REJECTED — no timezone
```

The models normalise both accepted forms to UTC on the way in.

### 2.2 `observed_at` is not `ingested_at`

| Field | Meaning | Drives |
| --- | --- | --- |
| `observed_at` | When it happened in the real world | Recency weighting (Epics 2 & 3) |
| `ingested_at` | When we wrote it down | Freshness monitoring (Task 6) |

Setting `observed_at = now()` makes every learner look equally recent and
breaks candidate ranking.

### 2.3 IDs are deterministic — never call `uuid4()`

```python
from src.app.graph.ids import deterministic_id

node_id = deterministic_id(source_system, source_type, source_id)
```

UUIDv5 hashes `(source_system, source_type, source_id)`, so the same source
record always yields the same UUID on any machine. Combined with `MERGE`, this
is what satisfies the Sprint 1 acceptance criterion *"backfill can be rerun
without duplicating events."*

A random UUID4 would create a new node on every run.

### 2.4 Every record carries provenance

```python
Provenance(
    source_system=SourceSystem.ASSESSMENT_ENGINE,
    source_id="lx-144bd399:12",              # primary key in the source
    source_type="interaction_log.feedback",  # record type
    source_locator="rubric_point:102",       # optional pointer inside it
    observed_at=entry_ts,
    ingested_at=now,
    extraction_method=ExtractionMethod.RULE_BASED,
)
```

Use `source_locator` for the exact spot inside a record — `turn:657`,
`entry_index:12`, `rubric_point:102`. Employers see these; they are how
"show me the evidence" lands on a real line of work.

### 2.5 Skill names are normalised before they reach the graph

The corpus contains `Python 3.11`, `python`, `Python`, `py`. Collapse to one
canonical name and keep the surface forms in `Skill.aliases`. Do not create
four `Skill` nodes.

---

## 3. ID property convention

Every node uses a single `id` property holding a UUIDv5 — **not** per-label
names like `learner_id` or `skill_id`.

Rationale:

- Task 3's batch loader stays generic. One `UNWIND … MERGE (n:Label {id: row.id})`
  works for all 25 labels instead of 25 special cases.
- The deterministic-ID scheme already encodes the source identity, so a second
  per-label key adds no information.
- Source identifiers are not lost: they are preserved on every node as
  `source_id` + `source_system`, and on `LearnerIdentity` for identity
  resolution.

This replaces the earlier placeholder in `src/app/graph/constraints.py`.
Raised for team review as part of this change.

---

## 4. Which source file feeds which node

### Task 4 — submissions & assessments

| Source | Produces | Key field mapping |
| --- | --- | --- |
| `learners.jsonl` | `Learner`, `LearnerIdentity`, `Round`, `Group` | `email`→`canonical_email`, `name`→`display_name`, `round_name`→`round_key`, `group_id`→`group_key` |
| `lx_configs.jsonl` | `TaskDefinition`, `LearningExperience`, `Rubric`, `RubricCriterion` | `lx_id`→`lx_key`, `task.headline`→`headline`, `task_definition_id`→`task_definition_key`, `status`/`outcome`→enums |
| `…rubric.scopes[]` | `RubricCriterion` | `criterion_key = "{task_def}:{scope.id}:{point.id}"` — must be globally unique |
| `interaction_logs.jsonl` → `entry.submission` | `Submission`, `Attempt`, `Artifact` | `kind`→`kind`, `text`→`text`/`submission_url`, `attachments`→`attachment_count` |
| `interaction_logs.jsonl` → `entry.feedback` | `Assessment`, `Evidence` | `verdict`→`verdict`, `summary`→`summary`, **`raw` → parse the JSON array** |
| `…feedback.raw` scope points | `Evidence` (one per point) | `reason`→`content`, `confidence_score`→`confidence`, `status`→`criterion_status`, `chunks_ids_met`→`Artifact` links |
| LMS *(not in current export)* | `Evidence`, tier `exposed` | tier, edges and DDL exist; nothing populates them yet |

**The grader payload is the richest source available.**
`entry.feedback.raw` contains a JSON array after the marker
`Scope Detailed Results:`. Each point already carries a claim, a confidence
score and artifact citations — evidence with provenance, pre-built. Parse it
with `json.JSONDecoder().raw_decode()`; the text following the array is not
valid JSON.

### Task 5 — meetings & agent chats

| Source | Produces | Key field mapping |
| --- | --- | --- |
| `meetings.jsonl` | `Meeting` | `meeting_id`→`meeting_key`, `kind`→`MeetingKind`, `starts_at_utc`→`starts_at_utc` |
| `meeting_memory_cards.jsonl` | `Evidence`, `Observation` | `content`→`content`/`behavior`, `confidence`→`confidence`, `source_locator`→`source_locator`, `rationale`→`outcome` |
| `interaction_logs.jsonl` (chat entries) | `Interaction` | `tags`→`tags`, `summary`→`summary`, `ts`→`occurred_at`, `actor_messages`→`message_count` |
| `transcripts/*.vtt` | `Evidence`, `Observation` | heavily Egyptian Arabic mixed with English technical terms |

**Type memory cards honestly.** A learner saying *"I'm using Remotion"* in a
standup is `SELF_DECLARED` / `LOW` — not demonstrated. Mapping talk to
`DEMONSTRATED` inflates every profile and destroys the tier system.
Behavioural cards are `OBSERVED_BEHAVIOR` / `MEDIUM`.

---

## 5. Required fields

Always required on every source-derived node:

```text
id · created_at · source_system · source_id · source_type
source_observed_at · ingested_at
```

Additionally:

| Node | Also required |
| --- | --- |
| `Learner` | `canonical_email`, `display_name` |
| `LearnerIdentity` | `source_learner_id` |
| `Round` / `Group` / `Cohort` | `*_key`, `name` |
| `TaskDefinition` | `task_definition_key`, `headline` |
| `LearningExperience` | `lx_key`, `status` |
| `Attempt` | `attempt_number`, `verdict` |
| `Submission` | `kind` |
| `Artifact` | `artifact_key` |
| `Rubric` / `RubricCriterion` | `rubric_key` / `criterion_key` |
| `Assessment` | `assessment_kind` |
| `Meeting` | `meeting_key`, `kind` |
| `Interaction` | `interaction_kind`, `occurred_at` |
| **`Evidence`** | `evidence_type`, `strength`, `title`, `content`, `observed_at` |
| `Skill` | `canonical_name`, `slug`, `category` — no provenance; it is a registry entry |
| `Observation` | `category`, `context`, `behavior`, `observed_at`, `computed_at`, `computed_by` |

---

## 6. Closed vocabularies

Import the enums rather than typing strings. Values follow the raw export
wherever one already existed.

| Enum | Allowed values |
| --- | --- |
| `SourceSystem` | `lms`, `virtual_internship`, `assessment_engine`, `meetings`, `meeting_memory`, `profile`, `scenario_engine`, `agent` |
| `EvidenceType` | `direct_assessment`, `delivered_work`, `observed_behavior`, `mentor_feedback`, `learning_exposure`, `self_declared` |
| `EvidenceStrength` | `high`, `medium_high`, `medium`, `low` |
| `SkillEvidenceTier` | `declared`, `exposed`, `assessed`, `demonstrated` |
| `AssertionStatus` | `no_evidence`, `weak`, `moderate`, `strong` |
| `LXStatus` | `active`, `terminated` |
| `LXOutcome` | `completed_success`, `completed_failed`, `expired`, `abandoned` |
| `AttemptVerdict` | `passed`, `failed_retry`, `failed_final`, `pending` |
| `CriterionStatus` | `Yes`, `Partial`, `No` — capitalised, matches the grader |
| `MeetingKind` | `sprint_planning`, `standup`, `retro`, `ad_hoc` |
| `AccessScope` | `internal_only`, `employer_shareable`, `learner_visible`, `restricted` |
| `ExtractionMethod` | `direct_mapping`, `rule_based`, `llm_extraction`, `human_curated` |

---

## 7. What gets rejected

| Input | Error |
| --- | --- |
| Naive timestamp | `timestamp must be timezone-aware ISO 8601` |
| Evidence with no provenance | `provenance → Field required` |
| `confidence = 1.4` | `Input should be less than or equal to 1` |
| Misspelled property | `Extra inputs are not permitted` |
| Skill claim with 0 evidence | `requires at least one evidence item; use status=no_evidence` |
| `no_evidence` + nonzero count | `status=no_evidence contradicts evidence_count=3` |
| Reversed relationship | `illegal relationship (Skill)-[:DEMONSTRATED_SKILL]->(Learner)` |
| `"the learner is lazy"` | `reads as a personality label, which PRD 8.2 forbids` |
| Evidence with no source link | `Evidence <id> has no DERIVED_FROM source record` |

The last one matters most. `LearnerGraph` refuses to build if any evidence
lacks a source or any claim lacks evidence. There is no bypass flag.

If a record cannot supply provenance it does not belong in the graph — surface
it in the failed-records queue instead. Sprint 1 requires unresolved records to
be **visible, not dropped**.

---

## 8. Known problems in the raw export

Found while building the seed fixture across all 14 learners in both groups.

| Count | Problem | Handling |
| --- | --- | --- |
| **246** | Real GitHub handle `MoHatemTC` survived anonymisation in `interaction_logs.jsonl` | **Scrub in the pipeline.** The export README flags glued strings as a known limit. |
| 47 | `task.technologies` empty | Fall back to `rubric.scopes[].requirement` — a better skill signal anyway |
| 31 | `extraction_status != done` on meetings | No transcript. Do not emit Evidence; mark pending |
| 18 | Task has no rubric scopes | `Rubric`/`RubricCriterion` optional — skip, still emit `TaskDefinition` |
| 17 | `status=terminated` with `outcome=null` | `outcome` is nullable by design. Leave null; do not guess |
| 10 | `attendee_emails` empty | Derive attendance from memory cards' `learner_id` |
| 1 | LX `1435355e` has `deadline_at` before `activated_at` | Source bug. Ingest as-is and flag; do not correct source truth |
| — | Two timestamp formats in one corpus | Normalise to UTC on the way in |
| — | Transcripts are Egyptian Arabic + English | Test extraction on Arabic before assuming an English pipeline works |

### Open question

`docs/data/data.md` lists three expected files:

```text
learners.jsonl   meeting_memory_cards.jsonl   interaction_logs.jsonl
```

**`lx_configs.jsonl` is missing.** That file holds every task definition,
rubric and rubric criterion. Without it, `TaskDefinition`, `Rubric` and
`RubricCriterion` cannot be populated and the assessment side of the graph is
lost. Needs a team decision.

---

## 9. Worked example

```python
from src.app.graph.schema import (
    AccessScope,
    Evidence,
    EvidenceStrength,
    EvidenceType,
    ExtractionMethod,
    Provenance,
    SourceSystem,
)
from src.app.graph.ids import evidence_uid

sid = f"{lx_id}:{entry_index}"

ev = Evidence(
    id=evidence_uid(
        "assessment_engine", "rubric_point", sid, scope_id, rubric_point_id
    ),
    created_at=now,
    provenance=Provenance(
        source_system=SourceSystem.ASSESSMENT_ENGINE,
        source_type="interaction_log.feedback.scope_point",
        source_id=sid,
        source_locator=f"scope:{scope_id}/rubric_point:{point_id}",
        observed_at=entry_ts,
        ingested_at=now,
        extraction_method=ExtractionMethod.RULE_BASED,
    ),
    evidence_type=EvidenceType.DIRECT_ASSESSMENT,
    strength=EvidenceStrength.HIGH,
    confidence=point["confidence_score"],
    title=f"Rubric point {point_id} scored '{status}'",
    content=point["reason"],
    observed_at=entry_ts,
    access_scope=AccessScope.EMPLOYER_SHAREABLE,
)
```

### Handing off to Task 3

`flatten_node()` converts any node into a flat map of primitives — exactly the
shape `UNWIND` needs as a query parameter. Verified JSON-serialisable with no
nested maps.

```python
from src.app.graph.serialization import flatten_node

rows = [flatten_node(n) for n in nodes if n.label == "Evidence"]
session.run(
    "UNWIND $rows AS row MERGE (n:Evidence {id: row.id}) SET n += row",
    rows=rows,
)
```

`src/app/graph/constraints.py` exposes `CONSTRAINTS`, `INDEXES`,
`FULLTEXT_INDEXES` and `ALL_STATEMENTS` as plain lists of Cypher strings for
schema initialisation, plus `ENTERPRISE_ONLY_CONSTRAINTS` for Enterprise
deployments only.

### A working reference implementation

`scripts/build_seed.py` reads the real export and produces 297 validated nodes
and 984 relationships. It is a **one-off fixture generator, not the production
pipeline** — but its parsing logic for the grader payload, memory cards and
attempt lineage is correct. Copy from it.

---

## 10. Verify your output

```bash
docker compose run --rm api python scripts/validate_seed.py   # 34 checks
docker compose run --rm api pytest                            # 43 tests
```
