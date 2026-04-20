"""PostgreSQL DDL — run via `albion-init-db`."""

from __future__ import annotations

import logging

import psycopg

logger = logging.getLogger(__name__)

DDL_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS game_patches (
      id SERIAL PRIMARY KEY,
      slug TEXT NOT NULL UNIQUE,
      label TEXT NOT NULL,
      starts_at TIMESTAMPTZ NOT NULL,
      ends_at TIMESTAMPTZ NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS kill_events (
      source_region TEXT NOT NULL,
      event_id BIGINT NOT NULL,
      time_stamp TIMESTAMPTZ NOT NULL,
      api_payload_version INT NULL,
      raw_json JSONB NOT NULL,
      patch_id INT NULL REFERENCES game_patches(id),
      ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (source_region, event_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_kill_events_time ON kill_events (time_stamp DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_kill_events_patch ON kill_events (patch_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS ingestion_cursors (
      source_region TEXT PRIMARY KEY,
      last_max_event_id BIGINT NULL,
      last_poll_at TIMESTAMPTZ NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS collector_runs (
      id BIGSERIAL PRIMARY KEY,
      started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      finished_at TIMESTAMPTZ NULL,
      status TEXT NOT NULL DEFAULT 'running',
      total_fetched INT NOT NULL DEFAULT 0,
      total_inserted INT NOT NULL DEFAULT 0,
      total_skipped_invalid INT NOT NULL DEFAULT 0,
      patch_rows_updated INT NOT NULL DEFAULT 0,
      error_message TEXT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_collector_runs_started
    ON collector_runs (started_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_collector_runs_status
    ON collector_runs (status)
    """,
]


async def apply_schema(conn: psycopg.AsyncConnection) -> None:
    async with conn.transaction():
        for stmt in DDL_STATEMENTS:
            await conn.execute(stmt)
    logger.info("Database schema applied (%s statements).", len(DDL_STATEMENTS))
