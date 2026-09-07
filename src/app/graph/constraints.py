"""
Neo4j constraints and indexes for the Professional Learner Graph (v2, minimal).

GENERATED FILE - produced by ``scripts/generate_constraints.py`` from
``src/app/graph/schema.py``. Do not hand-edit; change the models and
regenerate so the database rules cannot drift from the Python contract.

3 node labels (DataSource, LearnerProfile, MemoryCard), Community Edition safe.
Every statement uses ``IF NOT EXISTS``, so applying these repeatedly is safe.

ontology version : 0.2.0
"""

from __future__ import annotations

from neo4j import Driver

#: Uniqueness constraints.
CONSTRAINTS: list[str] = [
    """
    CREATE CONSTRAINT c_datasource_id_unique IF NOT EXISTS
    FOR (n:DataSource) REQUIRE n.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT c_learnerprofile_id_unique IF NOT EXISTS
    FOR (n:LearnerProfile) REQUIRE n.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT c_memorycard_id_unique IF NOT EXISTS
    FOR (n:MemoryCard) REQUIRE n.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT c_datasource_bkey_unique IF NOT EXISTS
    FOR (n:DataSource) REQUIRE n.datasource_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT c_learnerprofile_bkey_unique IF NOT EXISTS
    FOR (n:LearnerProfile) REQUIRE n.learner_id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT c_memorycard_bkey_unique IF NOT EXISTS
    FOR (n:MemoryCard) REQUIRE n.card_id IS UNIQUE
    """,
]

#: Range indexes on common lookups.
INDEXES: list[str] = [
    """
    CREATE INDEX i_datasource_datasource_name IF NOT EXISTS
    FOR (n:DataSource) ON (n.datasource_name)
    """,
    """
    CREATE INDEX i_datasource_timestamp IF NOT EXISTS
    FOR (n:DataSource) ON (n.timestamp)
    """,
    """
    CREATE INDEX i_learnerprofile_name IF NOT EXISTS
    FOR (n:LearnerProfile) ON (n.name)
    """,
    """
    CREATE INDEX i_learnerprofile_role IF NOT EXISTS
    FOR (n:LearnerProfile) ON (n.role)
    """,
    """
    CREATE INDEX i_learnerprofile_group_name IF NOT EXISTS
    FOR (n:LearnerProfile) ON (n.group_name)
    """,
    """
    CREATE INDEX i_learnerprofile_round_name IF NOT EXISTS
    FOR (n:LearnerProfile) ON (n.round_name)
    """,
    """
    CREATE INDEX i_memorycard_metric_key IF NOT EXISTS
    FOR (n:MemoryCard) ON (n.metric_key)
    """,
    """
    CREATE INDEX i_memorycard_created_at IF NOT EXISTS
    FOR (n:MemoryCard) ON (n.created_at)
    """,
]

#: Full-text search indexes.
FULLTEXT_INDEXES: list[str] = [
    """
    CREATE FULLTEXT INDEX ft_memorycard IF NOT EXISTS
    FOR (n:MemoryCard) ON EACH [n.content, n.rationale]
    """,
]

#: Every statement, in order. All of it is safe on Neo4j 5 Community.
ALL_STATEMENTS: list[str] = CONSTRAINTS + INDEXES + FULLTEXT_INDEXES


def initialize_schema(driver: Driver) -> None:
    """Apply every constraint and index. Safe to call more than once -
    every statement is ``IF NOT EXISTS``, so a second call is a no-op
    rather than an error."""
    with driver.session() as session:
        for statement in ALL_STATEMENTS:
            session.run(statement)
