# Task 24 — local integration verification

Status: partial verification, **not an end-to-end-on-main sign-off**.

## Revision and environment

- Tested local `feature/talent-history-integration`, including commit `2c5ec5c`.
- Fetched `origin/main` is `ced009e`; it does not contain `2c5ec5c`.
  Verify PR #34 landing or an equivalent superseding implementation before
  claiming main satisfies the conversation-history deliverable.
- PostgreSQL, Neo4j, Redis, and API ran in Docker. Alembic upgrade reached
  `c182fa0439be` in local PostgreSQL.
- Local `postgres:16` image was corrupt (empty entrypoint). Verification used
  a temporary Compose override with official `postgres:16-bookworm`, not a
  committed change to the team's Compose file.
- Credentials remained in ignored local `.env`; no credentials are recorded here.

## Verified

### API, history, and visual delegation

`scripts/verify_chat_live.py` called real signup, signin, conversation creation,
three chat turns, and message retrieval against the running API. No mocked
retrieval or LLM was injected. Clean verification conversation: **2**.

- Registration and login succeeded.
- Explicit learner selection persisted in PostgreSQL.
- A subsequent question omitted selection and asked about "his" strengths;
  manual review confirmed the answer cited the same learner's retrieved reviews.
- A bar-chart request returned one artifact with no fallback.
- All six user/assistant messages persisted.
- Talent tool-loop/model/tool spans appeared in the existing `Hiring Agent`
  LangSmith project. Additional local instrumentation now joins conversation
  and delegation spans and records the worker/synthesis path (details below).

The graph was loaded manually from the repository's anonymized `docs/data`
exports using its existing graph builder/loader. That builder adds seven
synthetic assessment records. Those generated records and their relationships
were removed from the local graph before the clean conversation was started;
zero `SYNTHETIC` DataSource payloads remained. Conversation 1 is an exploratory
run and must **not** be used as clean demo evidence.

Re-run inside the API container:

```sh
python -m scripts.verify_chat_live 127c834c-f7ce-4cc7-9a73-c8f93c8648aa
```

The script creates a unique verification account and retains its conversation.
It asserts response/artifact presence and persistence; semantic answer correctness
still requires inspection, rather than being inferred from HTTP success alone.

### Profile-update worker

`scripts/verify_profile_worker_live.py` dispatched a real Celery message through
Redis and verified live LLM synthesis and Neo4j persistence.

- Task ID: `7088116c-dda8-42a1-8ea7-c8f76c15ee5b`.
- Dedicated learner: `task24-verification-dadd6d65-af40-4b45-9468-47a4c7416bd6`.
- Target metric, evidence ID, checkpoint, and identical untouched metric passed.
- Dedicated test learner was deactivated afterwards; verification worker stopped.
- Beat registration inspected: Sunday 03:00, timezone `Africa/Cairo`.
- Beat was not left running and a whole-cohort update was not dispatched.

This worker check uses an explicitly dedicated test record, not demo fallback
data. A subsequent run verified the new worker/synthesis spans as described below.

## Follow-up implementation and live checks

The follow-up changes implement Sarah's soft-default request:

- Exact graph name/ID in a message updates the saved canonical learner ID.
- Multi-learner/comparison requests preserve the saved default.
- Duplicate names and pronoun references without a default clarify rather than guess.
- Database errors are propagated, and failed answers roll back selection/message writes.
- These changes need review in PR #34 before merge.

Live conversation **3** repeated the three-turn API smoke test successfully,
including a chart with no fallback and six persisted messages. Live conversation
**4** verified switching via a name in the message, followed by a comparison;
direct PostgreSQL assertions confirmed the saved selection after both turns.

Subsequent live worker task: `c1bd5884-7c1a-43d8-8d10-bacd41d40361`.
Dedicated learner: `task24-verification-7ea4e923-b573-4261-8f7c-32ec46ff05e3`.
Synthesis, persistence, checkpoint, and untouched-metric preservation passed.
The learner was deactivated and the temporary worker stopped.

Successful spans queried from the existing `Hiring Agent` project:

- `profile_update_worker`: `01a0caa8-a2fd-7381-a5b1-052ff2976f21`.
- `profile_metric_synthesis`: `01a0caa8-a41c-7732-ae6b-f62c3e22afc9`,
  parent is the worker span above.
- `talent_conversation`: `01a0caa8-a100-7dc3-a135-762e97e4dd73`.
- `visualizer_delegation`: `01a0caa9-28fd-7cb1-9225-901d2381af59`,
  parent is the conversation span above.

The explicit synthesis span covers the shared structured-output call; this is
not a claim that every low-level raw OpenAI request has its own LLM span.

### Regression checks

Targeted suites: `test_talent_history.py`, `test_visual_delegation.py`,
`test_periodic_profiles.py`, `test_periodic_profiles_storage.py`.
Initial result: **42 passed, 1 skipped** with isolated SQLite configuration.
After the soft-default changes, the expanded eight-suite run passed
**110 tests, 1 skipped** (chat, learner context, orchestration, history,
delegation, periodic service/storage, and Task 10 transformation).
Ruff and Black passed on changed files; targeted MyPy passed on six source files.
This is not a claim that the full repository suite or CI is green.

## Remaining integration work / coordination

1. Confirm PR #34 has actually landed on main or identify its replacement.
2. Frontend chat currently maps `/chat` directly as `BackendMessage`, whereas
   the API returns `{message, response}` with structured artifacts. Coordinate
   the response-envelope mapping with Mohamed El-Gazzar and test in-browser.
3. Confirm one-command startup and automatic graph loading with Mohamed Atia;
   this verification used manual loading and has not established fresh-clone startup.
4. Review and land the new soft-default and tracing changes, then repeat these
   checks on main. Existing trace IDs prove the local run, not a main deployment.
5. Capture the complete browser conversation and associated execution trace.

No remote merge was performed during this verification. No frontend or
shared LLM client was changed. Existing LangSmith instrumentation was extended
locally at owned service/agent boundaries. These remaining items prevent declaring
Task 24 fully complete on main.
