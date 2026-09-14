# Task 14 — weekly profile updates

Celery Beat publishes `profiles.dispatch` every **Sunday at 03:00 Africa/Cairo**.
The IANA timezone follows daylight saving; this is not a fixed UTC schedule.
Run **one Beat instance**. Redis carries JSON messages. The dispatcher publishes
one `profiles.update(learner_id)` message per active learner, so one failing
learner does not stop the others. No changes to the Task 10 AI workflow are needed.

## Run

Configure `.env` with the existing Neo4j and Task 10 AI settings
(`NEO4J_PASSWORD`, `AI_AGENT_URL`, `AI_API_KEY`, `PRIMARY_MODEL`). Then:

```sh
docker compose up -d --build redis profile-worker profile-beat
docker compose logs -f profile-worker profile-beat
```

This starts Neo4j as a dependency, not PostgreSQL. Worker images contain the code;
rebuild after edits. Stop scheduling with `docker compose stop profile-beat`.
To intentionally run all active learners immediately (uses the configured AI):

```sh
docker compose exec profile-worker celery -A src.app.workers.celery_app:app call profiles.dispatch
```

For direct local execution install `pip install -e '.[dev]'`, configure
`CELERY_BROKER_URL` (default `redis://localhost:6379/0`), and run separate terminals:

```sh
celery -A src.app.workers.celery_app:app worker --loglevel=INFO
celery -A src.app.workers.celery_app:app beat --loglevel=INFO
```

## Storage contract

`ProfileStorage` isolates storage from orchestration. The Neo4j implementation
uses the existing shared driver, not the investigation tools that suppress errors.
An explicit `is_active` flag takes precedence; otherwise `status` or legacy
`learner_status` must equal `active`. Missing activity is not assumed active.

Profiles reside on `LearnerProfile` nodes keyed by `learner_id`:

- `metrics_json`: JSON dictionary of Task 10 metric objects.
- `last_successful_profile_update_at`: ISO UTC successful cutoff.
- `profile_update_version`: integer optimistic version, initially zero.

Memory cards are read through `HAS_MEMORY_CARD` and legacy
`PRODUCED -> DataSource -> EXTRACTED_INTO`, deduplicating graph paths.
The source `card_id` is used, not the graph node ID. Missing/invalid timestamps
fail the learner rather than silently discarding evidence.

First run processes all available cards up to the run start. Later runs exclude
already recorded evidence IDs. Because the graph has no reliable ingestion-time
field, the repository scans linked cards, also catching unseen **backdated** cards
that a strict `created_at > checkpoint` query would miss. Future-dated cards wait.
This is correctness-first; a future ingestion cursor can optimize the scan.

Task 10 receives the previous profile and unseen cards. Its output is checked
for untouched-metric and metadata preservation. Storage preserves unchanged raw
metric objects and writes metrics plus checkpoint in **one transaction**, after
locking and comparing the original version, metrics, and checkpoint. Concurrent
stale updates retry from fresh state. No new cards means no AI call and a successful
checkpoint-only save. Failed synthesis or persistence never advances the checkpoint.

`PROFILE_UPDATE_MAX_RETRIES` defaults to 3, `PROFILE_UPDATE_RETRY_SECONDS` to 30;
countdowns double up to 300 seconds. Exhausted errors remain failed tasks; their
evidence remains eligible next cycle. Publish failure retries the dispatcher after
attempting the remaining learners. Repeated jobs are safe via evidence IDs/versioning.
Logs contain JSON event messages, learner/task identifiers, retry count and exception
tracebacks on failure. Card contents and credentials are not explicitly logged.

## Tests

```sh
pytest tests/test_periodic_profiles.py tests/test_periodic_profiles_storage.py -v
```

Unit tests use fake storage, synthetic cards, and mocked AI/broker calls. The
optional `NEO4J_URI=bolt://localhost:7687 TASK14_NEO4J_TEST=1 pytest tests/test_periodic_profiles_storage.py -v`
creates and removes one uniquely named synthetic learner and card to validate atomic
checkpointing; it does not call the AI or update real learner profiles.

The shared test configuration supplies a temporary SQLite database for API tests.
For live Neo4j tests, load the actual environment credentials before pytest starts;
otherwise the shared configuration defaults to the test password. After merging
main, 181 tests passed, one skipped, and six existing ingestion tests failed because
`settings.graph_loader_batch_size` is missing from the shared configuration.
The Task 10/14 tests pass, including the opt-in Neo4j persistence test.

References: [Celery periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html)
and [task retries](https://docs.celeryq.dev/en/stable/userguide/tasks.html).
