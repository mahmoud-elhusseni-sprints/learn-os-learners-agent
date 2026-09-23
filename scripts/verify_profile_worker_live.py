"""Opt-in live worker verification on a dedicated learner; no mocks.

Run inside the profile-worker container. Requires running Redis/Neo4j and a
configured LLM. Creates a uniquely named test learner, never dispatches the
whole cohort, and deactivates its test learner when finished. Prints IDs for
trace/log correlation; does not print credentials or learner card content.
"""

import json
import time
from uuid import uuid4

from src.app.graph.connections import get_driver
from src.app.workers.celery_app import app


def main() -> None:
    learner = "task24-verification-" + str(uuid4())
    untouched = {
        "summary": "Dedicated test baseline",
        "confidence": 0.5,
        "evidence_ids": ["test-baseline"],
        "custom": "must remain identical",
    }
    driver = get_driver()
    with driver.session() as session:
        session.run(
            "CREATE (l:LearnerProfile {learner_id:$id, name:$id, "
            "is_active:true, metrics_json:$metrics}) "
            "CREATE (l)-[:HAS_MEMORY_CARD]->(:MemoryCard {card_id:$id, "
            "metric_key:'python', content:'Completed a Python exercise with "
            "a passing unit test', rationale:'Observed test result', "
            "tags:['technical_skills'], "
            "created_at:datetime('2026-09-20T12:00:00Z')})",
            id=learner,
            metrics=json.dumps({"docker": untouched}),
        ).consume()
    print("TEST_LEARNER", learner, flush=True)
    try:
        task = app.send_task("profiles.update", args=[learner], queue="profile_updates")
        print("TASK_ID", task.id, flush=True)
        for _ in range(90):
            with driver.session() as session:
                row = session.run(
                    "MATCH (l:LearnerProfile {learner_id:$id}) "
                    "RETURN l.metrics_json AS metrics, "
                    "l.last_successful_profile_update_at AS checkpoint",
                    id=learner,
                ).single()
            if row and row["checkpoint"]:
                metrics = json.loads(row["metrics"])
                assert metrics["docker"] == untouched
                assert learner in metrics["python"]["evidence_ids"]
                print("PASS: live synthesis, persistence, checkpoint and preservation")
                return
            time.sleep(2)
        raise RuntimeError("No successful checkpoint within 180 seconds")
    finally:
        with driver.session() as session:
            session.run(
                "MATCH (l:LearnerProfile {learner_id:$id}) SET l.is_active=false",
                id=learner,
            ).consume()
        driver.close()


if __name__ == "__main__":
    main()
