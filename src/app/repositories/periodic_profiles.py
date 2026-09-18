"""Neo4j profile storage with atomic checkpointing and stale-write protection."""

import json
from datetime import datetime
from typing import Any

from src.app.schemas.models import LearnerProfile, MemoryCard
from src.app.services.periodic_profiles import Snapshot

ACTIVE = "coalesce(l.is_active, coalesce(l.status, l.learner_status) = 'active', false)"


class ConcurrentProfileUpdate(RuntimeError):
    """Another run changed this profile; reload before trying again."""


class Neo4jProfileStorage:
    def __init__(self, driver: Any) -> None:
        self.driver = driver

    def active_ids(self) -> list[str]:
        with self.driver.session() as session:
            return [
                row["id"]
                for row in session.run(
                    f"MATCH (l:LearnerProfile) WHERE {ACTIVE} "
                    "RETURN DISTINCT l.learner_id AS id ORDER BY id"
                )
                if row["id"]
            ]

    def load(self, learner_id: str) -> Snapshot | None:
        with self.driver.session() as session:
            rows = list(
                session.run(
                    f"MATCH (l:LearnerProfile {{learner_id: $id}}) WHERE {ACTIVE} "
                    "RETURN properties(l) AS props",
                    id=learner_id,
                )
            )
        if not rows:
            return None
        if len(rows) != 1:
            raise ValueError("Duplicate learner IDs")
        props = dict(rows[0]["props"])
        raw = props.pop("metrics_json", "{}")
        checkpoint = props.pop("last_successful_profile_update_at", None)
        version = props.pop("profile_update_version", 0)
        # Graph-native temporal values must be converted before Pydantic validation.
        props = {
            k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in props.items()
        }
        props["metrics"] = json.loads(raw)
        return Snapshot(LearnerProfile.model_validate(props), raw, checkpoint, version)

    def cards(self, learner_id: str) -> list[MemoryCard]:
        with self.driver.session() as session:
            rows = list(
                session.run(
                    "MATCH (l:LearnerProfile {learner_id: $id}) "
                    "CALL (l) { MATCH (l)-[:HAS_MEMORY_CARD]->(m:MemoryCard) RETURN m "
                    "UNION MATCH (l)-[:PRODUCED]->(:DataSource)"
                    "-[:EXTRACTED_INTO]->(m:MemoryCard) RETURN m } "
                    "RETURN DISTINCT properties(m) AS props",
                    id=learner_id,
                )
            )
        cards = []
        for row in rows:
            props = row["props"]
            value = {
                key: props.get(key)
                for key in (
                    "card_id",
                    "meeting_id",
                    "metric_key",
                    "content",
                    "rationale",
                    "created_at",
                )
            }
            timestamp = value["created_at"]
            if hasattr(timestamp, "to_native"):
                value["created_at"] = timestamp.to_native()
            value["tags"] = props.get("tags") or []
            cards.append(MemoryCard.model_validate(value))
        return cards

    def save(
        self,
        learner_id: str,
        snapshot: Snapshot,
        profile: LearnerProfile,
        cutoff: datetime,
    ) -> None:
        """Lock, compare, and save in one transaction; exceptions roll back."""

        def commit(tx: Any) -> None:
            rows = list(
                tx.run(
                    f"MATCH (l:LearnerProfile {{learner_id: $id}}) WHERE {ACTIVE} "
                    "SET l.profile_update_version = "
                    "coalesce(l.profile_update_version, 0) "
                    "RETURN l.metrics_json AS metrics, "
                    "l.profile_update_version AS version, "
                    "l.last_successful_profile_update_at AS checkpoint",
                    id=learner_id,
                )
            )
            if len(rows) != 1:
                raise ConcurrentProfileUpdate("Learner missing, inactive or duplicated")
            row = rows[0]
            if (
                (row["metrics"] or "{}") != snapshot.metrics_json
                or row["version"] != snapshot.version
                or row["checkpoint"] != snapshot.checkpoint
            ):
                raise ConcurrentProfileUpdate("Profile changed during synthesis")
            # Preserve the exact stored objects for all unchanged metrics.
            merged = json.loads(snapshot.metrics_json)
            for key, metric in profile.metrics.items():
                if metric != snapshot.profile.metrics.get(key):
                    merged[key] = metric.model_dump(mode="json")
            tx.run(
                "MATCH (l:LearnerProfile {learner_id: $id}) "
                "SET l.metrics_json=$metrics, l.profile_update_version=$version, "
                "l.last_successful_profile_update_at=$checkpoint",
                id=learner_id,
                metrics=json.dumps(merged),
                version=snapshot.version + 1,
                checkpoint=cutoff.isoformat(),
            ).consume()

        with self.driver.session() as session:
            session.execute_write(commit)
