"""
Neo4j driver lifecycle.

One driver, created once and reused for the life of the process. The
official driver already pools connections internally (its default pool
size is more than enough here) - a *new* driver per call would open a new
pool every time and defeats that, which is exactly what this module exists
to avoid.
"""

from __future__ import annotations

from neo4j import Driver, GraphDatabase

from src.app.core.config import settings

_driver: Driver | None = None


def get_driver() -> Driver:
    """Return the shared driver, creating it on first use."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
    return _driver


def close_driver() -> None:
    """Close the shared driver, if one was created. Safe to call more than
    once (e.g. from both a shutdown hook and a test's teardown)."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
