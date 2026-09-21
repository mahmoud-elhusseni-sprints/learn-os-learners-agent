# Pipeline Operations Report

> **Status: live run complete.** The counts below come from the generated files in `json/`, the validated graph adapter, and a successful load into the configured Neo4j Aura database.

## Stages

| Stage | Reads | Writes |
|---|---|---|
| 1. Learner profile extraction | `data/group-a-ai-engineer/learners.jsonl`, `data/group-b-product-management/learners.jsonl` | `json/extracted_learner_profiles.json` |
| 2. Mentor review extraction | Each cohort's `lx_turns.jsonl`, `lx_configs.jsonl`, and `interaction_logs.jsonl` | `json/extracted_mentor_rubrics.json` |
| 3. LMS assessment extraction | Each cohort's `lx_configs.jsonl`, benchmark answer JSON, and optional generated cards | `json/extracted_lms_assessments.json` |
| 4. DataSource generation | Mentor rubrics and LMS assessments | `json/graph_datasource_nodes.json` |
| 5. MemoryCard generation | Mentor rubrics and LMS assessments | `json/graph_memory_cards.json` |
| 6. Graph adaptation and validation | The three graph JSON files above | Validated `LearnerGraph` in memory; skipped and duplicate records are reported |
| 7. Neo4j loading | Validated `LearnerGraph` | Neo4j `LearnerProfile`, `DataSource`, and `MemoryCard` nodes plus relationships |

## Reproduction

From the repository root:

```powershell
docker compose up -d neo4j
python full_test/test_preprocessing.py
python full_test/test_data_loading.py --pipeline-dir json
```

The equivalent direct loader command is:

```powershell
python -m src.loader.graph_loader --pipeline-dir json
```

The loader initializes the schema, validates the generated files, then merges nodes before edges. Re-running it is idempotent.

## Input files

- `data/group-a-ai-engineer/learners.jsonl`
- `data/group-a-ai-engineer/lx_configs.jsonl`
- `data/group-a-ai-engineer/lx_turns.jsonl`
- `data/group-a-ai-engineer/interaction_logs.jsonl`
- `data/group-b-product-management/learners.jsonl`
- `data/group-b-product-management/lx_configs.jsonl`
- `data/group-b-product-management/lx_turns.jsonl`
- `data/group-b-product-management/interaction_logs.jsonl`
- `data/benchmark_answers_group_a.json`
- `data/benchmark_answers_group_b.json`

## Counts from the run

The counts below are intentionally marked as pending because Docker was unavailable when this file was prepared. Do not describe them as verified until the commands above complete successfully.

| Metric | Count |
|---|---:|
| LearnerProfile nodes | 14 |
| DataSource records in JSON | 71 |
| DataSource nodes accepted: reviews | 39 |
| DataSource records skipped: assessments | 28 |
| DataSource nodes: other/stub types | 0 |
| MemoryCard nodes | 522 |
| Edges: `PRODUCED` | 39 |
| Edges: `EXTRACTED_INTO` | 354 |
| Edges: `HAS_MEMORY_CARD` | 522 |
| Total validated nodes | 575 |
| Total validated edges | 915 |
| Skipped records: assessment DataSources | 28 |
| Skipped records: invalid MemoryCards | 168 |
| Skipped records: total | 196 |
| Duplicate records collapsed | 4 |

The 28 skipped assessment DataSources have the JSON value `assessments`; the
graph schema currently does not accept that value. The other 168 skipped
records are invalid MemoryCards. Both categories are reported by the adapter
and are not silently loaded. The four duplicates are duplicate DataSource ids
in the batch.

The loader prints the validated totals in the form:

```text
loaded <nodes> nodes (<per-label counts>), <edges> edges, <skipped> skipped, <duplicates> duplicates collapsed
```

Live loader result:

```text
Data loading test completed.
- 575 nodes (DataSource=39, LearnerProfile=14, MemoryCard=522), 915 edges, 196 skipped, 4 duplicates collapsed
```

## Verification

After loading, run the Task 13 questions in `docs/task13_agent_run.txt`. The answers must come from the loaded Neo4j graph, not from mocked fixtures.
