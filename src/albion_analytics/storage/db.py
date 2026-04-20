"""Database connection helpers."""

from __future__ import annotations

import asyncio
import logging

import psycopg

from albion_analytics.config import Settings, get_settings

logger = logging.getLogger(__name__)


async def connect_database(settings: Settings | None = None) -> psycopg.AsyncConnection:
    """Connect to Postgres with startup retries for managed deployment platforms."""
    s = settings or get_settings()
    if not s.database_url:
        raise ValueError("DATABASE_URL is not set")

    last_error: Exception | None = None
    attempts = max(1, s.database_connect_max_retries + 1)

    for attempt in range(1, attempts + 1):
        try:
            return await psycopg.AsyncConnection.connect(s.database_url)
        except psycopg.OperationalError as exc:
            last_error = exc
            if attempt >= attempts:
                break
            logger.warning(
                "Database connection failed attempt=%s/%s; retrying in %.1fs: %s",
                attempt,
                attempts,
                s.database_connect_retry_delay_sec,
                exc,
            )
            await asyncio.sleep(s.database_connect_retry_delay_sec)

    if last_error is not None:
        raise last_error
    raise RuntimeError("Database connection failed without an exception")
