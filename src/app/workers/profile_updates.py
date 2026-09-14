"""One independent Celery message per learner; bounded retries on failures."""

import json
import logging
import os
from typing import Any

from src.app.workers.celery_app import app

logger = logging.getLogger(__name__)
MAX_RETRIES = int(os.getenv("PROFILE_UPDATE_MAX_RETRIES", "3"))
RETRY_SECONDS = int(os.getenv("PROFILE_UPDATE_RETRY_SECONDS", "30"))


def storage() -> Any:
    """Resolve the driver inside the worker, not in the parent before fork."""
    from src.app.graph.connections import get_driver
    from src.app.repositories.periodic_profiles import Neo4jProfileStorage

    return Neo4jProfileStorage(get_driver())


def agent() -> Any:
    from src.app.agents.learner_profile_update.agent import (
        LearnerProfileUpdateAgent,
        LLMMetricSynthesizer,
    )

    return LearnerProfileUpdateAgent(LLMMetricSynthesizer.from_env())


class LazyProfileAgent:
    """No AI configuration or client is needed when there are no new cards."""

    def update(self, request: Any) -> Any:
        return agent().update(request)


@app.task(bind=True, name="profiles.dispatch", max_retries=MAX_RETRIES)
def dispatch(self: Any) -> dict[str, int]:
    """Publish independent jobs; a failed learner never blocks another."""
    try:
        ids = storage().active_ids()
        failed = 0
        for learner_id in ids:
            try:
                update.delay(learner_id)
            except Exception:
                failed += 1
                logger.exception(
                    json.dumps({"event": "enqueue_failed", "learner_id": learner_id})
                )
        if failed:
            raise RuntimeError("Some learner messages could not be published")
        logger.info(json.dumps({"event": "batch_dispatched", "count": len(ids)}))
        return {"queued": len(ids)}
    except Exception as exc:
        # Republished jobs are safe: evidence IDs and atomic versions prevent loss.
        raise self.retry(
            exc=exc, countdown=min(300, RETRY_SECONDS * 2**self.request.retries)
        ) from exc


@app.task(bind=True, name="profiles.update", max_retries=MAX_RETRIES)
def update(self: Any, learner_id: str) -> dict[str, Any]:
    """Persist a complete update or retry without moving its checkpoint."""
    from src.app.services.periodic_profiles import update_learner

    try:
        result = update_learner(learner_id, storage(), LazyProfileAgent())
        logger.info(
            json.dumps(
                {"event": "profile_update", "task_id": self.request.id, **result}
            )
        )
        return result
    except Exception as exc:
        logger.exception(
            json.dumps(
                {
                    "event": "profile_update_failed",
                    "learner_id": learner_id,
                    "task_id": self.request.id,
                    "retry": self.request.retries,
                    "error_type": type(exc).__name__,
                }
            )
        )
        raise self.retry(
            exc=exc, countdown=min(300, RETRY_SECONDS * 2**self.request.retries)
        ) from exc
