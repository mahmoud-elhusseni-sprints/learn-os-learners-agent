"""
Application configuration, read from the environment / ``.env``.

Only Neo4j settings live here for now - the other env vars in
``.env.example`` (Hugging Face, AI agent) belong to other tasks and are
read wherever those tasks need them, not centralised here speculatively.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str

    #: Connection pool sizing and timeouts. Defaults match the driver's own
    #: defaults; override per deployment rather than in code.
    neo4j_max_connection_pool_size: int = 100
    neo4j_connection_acquisition_timeout: float = 60.0

    #: Rows per Cypher statement in the batch loader. Keeps a single
    #: transaction's payload bounded on large ingestion runs.
    graph_loader_batch_size: int = 1000


settings = Settings()  # type: ignore[call-arg]  # values come from env/.env, not kwargs
