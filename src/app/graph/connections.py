"""
Neo4j driver lifecycle.

One driver, created once and reused for the life of the process. The
official driver already pools connections internally - a *new* driver per
call would open a new pool every time and defeat that, which is exactly
what this module exists to avoid.

Pool sizing and connection timeouts are configurable through the
environment (see ``src/app/core/config.py``) so a deployment can tune them
without a code change.
"""

from __future__ import annotations

import logging

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable

from src.app.core.config import settings

logger = logging.getLogger(__name__)

__all__ = ["get_driver", "close_driver", "verify_connection", "GraphConnectionError"]

_driver: Driver | None = None


class GraphConnectionError(RuntimeError):
    """Raised when the graph database cannot be reached or authenticated.

    Wraps the driver's own exceptions so callers get one error type with a
    message that says which URI failed and what to check, instead of a bare
    ``ServiceUnavailable`` from deep inside the driver.
    """


def get_driver() -> Driver:
    """Return the shared driver, creating it on first use."""
    global _driver
    if _driver is None:
        try:
            _driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
                max_connection_pool_size=settings.neo4j_max_connection_pool_size,
                connection_acquisition_timeout=(
                    settings.neo4j_connection_acquisition_timeout
                ),
            )
        except ValueError as exc:  # malformed URI / scheme
            raise GraphConnectionError(
                f"invalid Neo4j connection configuration for "
                f"{settings.neo4j_uri!r}: {exc}"
            ) from exc
        logger.debug("opened Neo4j driver for %s", settings.neo4j_uri)
    return _driver


def verify_connection(driver: Driver | None = None) -> None:
    """Check the database is reachable and the credentials work.

    Call this at startup (or before a long ingestion run) so a bad URI or
    password fails immediately with a clear message, instead of surfacing
    partway through a batch.
    """
    driver = driver or get_driver()
    try:
        driver.verify_connectivity()
    except AuthError as exc:
        raise GraphConnectionError(
            f"Neo4j rejected the credentials for user "
            f"{settings.neo4j_username!r} at {settings.neo4j_uri} - check "
            f"NEO4J_USERNAME / NEO4J_PASSWORD"
        ) from exc
    except ServiceUnavailable as exc:
        raise GraphConnectionError(
            f"Neo4j is not reachable at {settings.neo4j_uri} - is the "
            f"container running? (`docker compose up -d neo4j`)"
        ) from exc


def close_driver() -> None:
    """Close the shared driver, if one was created. Safe to call more than
    once (e.g. from both a shutdown hook and a test's teardown)."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.debug("closed Neo4j driver")
