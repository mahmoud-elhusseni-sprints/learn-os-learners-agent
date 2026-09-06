# Professional Learner Graph - Ontology Reference

- ontology version: `0.2.0`
- schema version: `learner-graph/0.2.0`
- node labels: **3** (DataSource, LearnerProfile, MemoryCard)
- relationship types: **3** across **3** legal endpoint pairs

> **Generated file.** Produced by `scripts/generate_docs.py` from
> `src/app/graph/schema.py`. Edit the models and regenerate; do not
> hand-edit this file.

This is the v2, minimal ontology: 3 node types (`LearnerProfile`, `DataSource`, `MemoryCard`), rewritten from a 26-node design per the mentor's rejection of the previous schema and the architecture specified in the mentor-authored MD file. See the module docstring in `src/app/graph/schema.py` for the full before/after rationale, including what was removed and why.

---

## 1. Node types

### `DataSource`

MD §2. One record from one of four source systems, keyed by
``datasource_name``. The embedded ``payload`` is where almost all of
the previous schema's separate node types now live.

| property | type | required | notes |
|---|---|---|---|
| `id` | `str` | yes | Deterministic id - see src/app/graph/ids.py |
| `created_at` | `datetime (UTC)` | yes |  |
| `datasource_id` | `str` | yes |  |
| `datasource_name` | `DataSourceName` | yes |  |
| `timestamp` | `datetime (UTC)` | yes |  |
| `payload` | `ReviewPayload \| AssessmentPayload \| StubPayload` | yes |  |

---

### `LearnerProfile`

MD §1. The canonical person and their programme placement.

| property | type | required | notes |
|---|---|---|---|
| `id` | `str` | yes | Deterministic id - see src/app/graph/ids.py |
| `created_at` | `datetime (UTC)` | yes |  |
| `learner_id` | `str` | yes | Source system's learner id |
| `name` | `str` | yes |  |
| `role` | `LearnerRole` | yes |  |
| `group_name` | `str` | yes |  |
| `round_name` | `str` | yes |  |
| `added_at` | `datetime (UTC)` | yes |  |
| `learner_status` | `str \| None` | no | Whether the learner is active. The MD file notes this 'can be removed' - kept as optional per tha... |

---

### `MemoryCard`

MD §3. A short, tagged insight extracted from a source record.

| property | type | required | notes |
|---|---|---|---|
| `id` | `str` | yes | Deterministic id - see src/app/graph/ids.py |
| `created_at` | `datetime (UTC)` | yes |  |
| `card_id` | `str` | yes |  |
| `metric_key` | `str` | yes |  |
| `content` | `str` | yes |  |
| `rationale` | `str \| None` | no |  |
| `tags` | `list[str]` | no | Corresponds to profile_hints in the dataset (MD file's own note). |

---

## 2. Embedded payload shapes

`DataSource.payload` is a discriminated union, chosen by `datasource_name` - never a separate node.

#### `ReviewPayload`

``datasource_name == "review"`` - Task Submission + Mentor Rubric
Evaluation, combined into one embedded object per the MD file.

| property | type | required | notes |
|---|---|---|---|
| `lx_id` | `str` | yes | Task / Learning Experience id |
| `task_headline` | `str` | yes |  |
| `attempt_number` | `int` | yes |  |
| `hours_before_deadline` | `float` | yes | Hours between submission and the task deadline. Negative means submitted late. |
| `submission_text` | `str` | yes |  |
| `assets` | `list[str]` | no | Combined code_repositories + media_assets per the MD file. |
| `verdict` | `str` | yes |  |
| `feedback_summary` | `str` | yes |  |
| `mentor_reply` | `str` | yes |  |
| `detailed_rubric_evaluations` | `list[RubricPointEvaluation]` | no |  |

#### `RubricPointEvaluation`

One entry in ``review`` payload's ``detailed_rubric_evaluations``.

| property | type | required | notes |
|---|---|---|---|
| `rubric_id` | `int` | yes |  |
| `category` | `str` | yes |  |
| `requirement` | `str` | yes |  |
| `status` | `RubricPointStatus` | yes |  |
| `evaluation_criteria` | `str` | yes |  |
| `reason` | `str` | yes |  |
| `confidence_score` | `float` | yes |  |

#### `AssessmentPayload`

``datasource_name == "assesments"`` - an LMS-style assessment.

| property | type | required | notes |
|---|---|---|---|
| `lx_id` | `str` | yes |  |
| `assessment_type` | `str` | yes |  |
| `topic_id` | `str` | yes |  |
| `score` | `float` | yes |  |
| `max_score` | `float` | yes |  |
| `answers` | `list[AssessmentAnswerItem]` | no |  |

#### `AssessmentAnswerItem`

One entry in ``assesments`` payload's ``answers``.

| property | type | required | notes |
|---|---|---|---|
| `question_id` | `str` | yes |  |
| `domain` | `str` | yes |  |
| `metric_key` | `str` | yes |  |
| `learner_answer` | `str` | yes |  |
| `score` | `float` | yes |  |
| `evaluation_notes` | `str` | yes |  |

#### `StubPayload`

``datasource_name in ("chat", "meetings")`` - owned by another task.

The MD file marks both as ``payload={}``. Modelled as an explicit empty
shape rather than an untyped dict, so a chat/meetings DataSource cannot
silently accumulate fields that belong to the review/assessment shapes.

| property | type | required | notes |
|---|---|---|---|

---

## 3. Relationships

Every relationship below is registered in `EDGE_SPECS`. An edge whose `(type, source, target)` triple is not in this table is **rejected at validation time**.

Cardinality is read left-to-right:

| notation | meaning |
|---|---|
| `1:1` | each source has at most one target, and vice versa |
| `1:N` | one source, many targets; each target has one source |
| `N:1` | many sources, one target; each source has one target |
| `N:M` | unconstrained both ways |

| relationship | cardinality | meaning |
|---|---|---|
| `(:DataSource)-[:EXTRACTED_INTO]->(:MemoryCard)` | `1:N` | One source record (e.g. a review with several rubric points, or an assessment with several answers) can be distilled into several memory cards. |
| `(:LearnerProfile)-[:HAS_MEMORY_CARD]->(:MemoryCard)` | `N:M` | Direct link from learner to memory card, drawn explicitly in the MD file's architecture notes as many-to-many, in addition to the indirect path via DataSource. |
| `(:LearnerProfile)-[:PRODUCED]->(:DataSource)` | `1:N` | A learner produces many source records over time. |

---

## 4. Controlled vocabularies

Values follow the source export wherever one already exists (including its misspellings, e.g. `assesments`), so ingestion never has to translate between two vocabularies.

**`Cardinality`** - str(object='') -> str

  `1:1`, `1:N`, `N:1`, `N:M`

**`DataSourceName`** - MD §2: the four named datasource_name values, verbatim.

  `review`, `assesments`, `chat`, `meetings`

**`EdgeType`** - str(object='') -> str

  `PRODUCED`, `EXTRACTED_INTO`, `HAS_MEMORY_CARD`

**`LearnerRole`** - MD §1: "role can be 'lead' or 'member'".

  `lead`, `member`

**`RubricPointStatus`** - Status values used inside a review payload's rubric evaluations.

  `Yes`, `Partial`, `No`

---

## 5. Invariants enforced in code

`LearnerGraph` refuses to construct a graph that breaks any of these:

1. every node id is unique;
2. every edge endpoint exists and its declared label matches the node;
3. every edge is a registered `(type, source, target)` triple;
4. declared cardinality holds;
5. `DataSource.payload`'s concrete type matches its `datasource_name` (`_payload_matches_datasource_name`);
6. an `assesments` payload's `score` never exceeds its `max_score` (`_score_within_max`).

There is **no** "Evidence-First" invariant in this version - the previous design's Evidence/SkillAssertion nodes do not exist here, so there is nothing analogous to enforce. A `DataSource`'s payload is trusted as delivered. See the schema module docstring for why this is a deliberate, flagged loss of guarantee rather than an oversight.

The same rules are expressed as Cypher constraints/indexes in `docs/data/schema_constraints.cql`.

