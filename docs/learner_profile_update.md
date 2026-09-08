# Task 10: Learner Profile Update Agent

This AI layer transforms one learner's prior profile plus new, already-tagged
memory cards into a new profile. It performs no database reads/writes, raw-log
extraction, learner investigation, or hiring decisions. It is separate from Task 6.

## Contracts

`ProfileUpdateInput` has `previous_profile` (null, `{}`, or a profile) and
`memory_cards` (a list). `MemoryCard` has exactly these fields:

- `card_id`: nonempty string; UUID objects are normalized to strings.
- `meeting_id`: nonempty string/UUID or null (default); null for non-meeting cards.
- `metric_key`: nonempty exact target key. No taxonomy or tag restriction.
- `content`: nonempty observation text.
- `rationale`: string explanation; not independent evidence.
- `tags`: list of descriptive strings, never update targets.
- `created_at`: timezone-aware datetime or ISO timestamp with UTC/offset.

Malformed dates, unknown card fields, empty keys and invalid confidence fail
Pydantic validation. Naive timestamps are rejected rather than assuming a zone.
The caller is responsible for providing cards belonging to the chosen learner:
the simplified seven-field contract contains no learner identity.

`LearnerProfile.metrics` is a dictionary keyed by exact `metric_key`. Each
`ProfileMetric` contains `summary`, `confidence` (finite number 0..1), and
`evidence_ids` (strings). Additional existing profile and metric metadata is
preserved, not regenerated. Identity is never invented for a null baseline.
This task-local model does not replace `app.models.deliverables.LearnerProfile`.
Callers adapting shared memory cards must explicitly select the seven fields and
supply a valid rationale/date; this agent does not guess missing source values.

## Transformation and guarantees

1. Deep-copy the request and previous profile; group cards by `metric_key`.
2. Reject inconsistent payloads sharing an ID in the batch; deduplicate exact copies.
3. Skip IDs already recorded for the target (idempotent replay).
4. Sort new cards by actual timestamp, using ID to break ties deterministically.
5. Ask the injected synthesizer for **only** summary and confidence for each target.
6. Validate the draft; merge only targeted fields in Python; retain old evidence
   IDs and append unique new IDs. Preserve extra metadata on targeted metrics too.
7. Return the new `LearnerProfile` only after all targets succeed.

Untargeted metrics retain identical serialized values, including extra fields and
evidence-list order. This is value/serialization preservation, not preservation of
the original input JSON whitespace. Output objects are deep copies, not aliases.
No cards means no model call and an unchanged profile; null plus no cards returns
`{"metrics": {}}`. Replayed historical IDs are treated as immutable: without raw
historical cards, their original content cannot be compared. Upstream must not
reuse IDs for corrections; send a new card ID instead.

## Prompt and evidence semantics

The prior summary/confidence are consolidated baseline context, not raw evidence.
The prompt combines them with new content/rationale/timestamps, describes
discrepancies, and never invents prior dates. New-card timestamps order those cards;
they cannot establish chronology against an undated prior summary. Tags and task
assignments do not prove proficiency. Confidence measures support for the summary,
not proficiency or a calibrated probability. Duplicate observations must not raise
confidence merely by repetition. Input text is untrusted data, not instructions.

The summary is the supporting-evidence synthesis; new observations should cite
supplied card IDs. Python owns the `evidence_ids` lineage list: it includes processed
cards, including conflicting or insufficient observations, not just positive proof.
The adapter cannot choose additional metric keys or evidence IDs.

The adapter requests strict JSON schema and validates the result with Pydantic.
Refusal, truncation, invalid JSON/schema and provider errors raise a safe
`ProfileUpdateError`; there is no fallback that presents failure as a successful
update. A successful return always satisfies the output schema. Schema validation
does **not** prove semantic truth; live outputs still need evidence-quality review.
Provider support for JSON schema must be verified on the configured LiteLLM model.

## Running

No dataset files are needed. All tests and the example below use synthetic data.
Using the project's Docker environment (no Neo4j dependency for this layer):

```bash
docker compose build api
docker compose run --rm --no-deps api pytest tests/test_learner_profile_update.py -v
docker compose run --rm --no-deps api python -m app.agents.learner_profile_update docs/examples/profile_update_request.json
```

The CLI only validates by default. To explicitly call the model, set existing
`AI_AGENT_URL`, `AI_API_KEY`, `AI_MODEL` in the root `.env` (or process environment):

```bash
docker compose run --rm --no-deps api python -m app.agents.learner_profile_update docs/examples/profile_update_request.json --live
```

Environment values override `.env`; credentials are never printed. Live mode sends
only the targeted baseline and cards to the configured provider. The model client
has a 45-second timeout and at most one SDK retry. Do not use real learner data in
public fixtures or commit `.env`. Local Python 3.11 alternative: install `.[dev]`
in an isolated environment, then run the same pytest/Python commands without Docker.

Programmatic use:

```python
from app.agents.learner_profile_update import (
    LearnerProfileUpdateAgent, ProfileUpdateInput,
)
from app.agents.learner_profile_update.llm_adapter import LiteLLMMetricSynthesizer

request = ProfileUpdateInput.model_validate(payload)
agent = LearnerProfileUpdateAgent(LiteLLMMetricSynthesizer.from_env())
updated_profile = agent.update(request)
# Caller decides whether/how to persist updated_profile; this module never does.
```

For unit tests, inject a fake `MetricSynthesizer` instead of the live adapter. The
tests cover null/empty initialization, single/multiple targets, untouched-field
regressions, input isolation, duplicates/replay, ordering, atomic errors, schema
validation, prompt context and adapter failures. Prompt assertions test the prompt
contract, not the model's actual compliance; inspect the live synthetic example
for conflicting-baseline handling before mentor review.

Structured-output reference used for the SDK request:
[OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
