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
    CREATE TABLE IF NOT EXISTS event_loadouts (
      source_region TEXT NOT NULL,
      event_id BIGINT NOT NULL,
      perspective TEXT NOT NULL,
      participant_index INT NOT NULL DEFAULT 0,
      time_stamp TIMESTAMPTZ NOT NULL,
      patch_id INT NULL REFERENCES game_patches(id),
      player_id TEXT NULL,
      player_name TEXT NULL,
      guild_id TEXT NULL,
      guild_name TEXT NULL,
      alliance_id TEXT NULL,
      alliance_name TEXT NULL,
      average_item_power DOUBLE PRECISION NULL,
      number_of_participants INT NULL,
      group_member_count INT NULL,
      total_victim_kill_fame BIGINT NULL,
      kill_fame BIGINT NULL,
      death_fame BIGINT NULL,
      build_key TEXT NULL,
      main_hand_type TEXT NULL,
      off_hand_type TEXT NULL,
      head_type TEXT NULL,
      armor_type TEXT NULL,
      shoes_type TEXT NULL,
      bag_type TEXT NULL,
      cape_type TEXT NULL,
      mount_type TEXT NULL,
      potion_type TEXT NULL,
      food_type TEXT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      PRIMARY KEY (source_region, event_id, perspective, participant_index),
      CONSTRAINT fk_event_loadouts_event
        FOREIGN KEY (source_region, event_id)
        REFERENCES kill_events (source_region, event_id)
        ON DELETE CASCADE,
      CONSTRAINT chk_event_loadouts_perspective
        CHECK (perspective IN ('killer', 'victim', 'participant'))
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_event_loadouts_time
    ON event_loadouts (time_stamp DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_event_loadouts_perspective_time
    ON event_loadouts (perspective, time_stamp DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_event_loadouts_patch
    ON event_loadouts (patch_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_event_loadouts_build
    ON event_loadouts (perspective, build_key)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_event_loadouts_main_hand
    ON event_loadouts (perspective, main_hand_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_event_loadouts_head
    ON event_loadouts (perspective, head_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_event_loadouts_armor
    ON event_loadouts (perspective, armor_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_event_loadouts_shoes
    ON event_loadouts (perspective, shoes_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_event_loadouts_cape
    ON event_loadouts (perspective, cape_type)
    """,
    """
    CREATE TABLE IF NOT EXISTS event_loadout_normalization_status (
      source_region TEXT NOT NULL,
      event_id BIGINT NOT NULL,
      normalized_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      row_count INT NOT NULL DEFAULT 0,
      skipped_reason TEXT NULL,
      PRIMARY KEY (source_region, event_id),
      CONSTRAINT fk_event_loadout_normalization_status_event
        FOREIGN KEY (source_region, event_id)
        REFERENCES kill_events (source_region, event_id)
        ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_event_loadout_normalization_status_at
    ON event_loadout_normalization_status (normalized_at DESC)
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
    """
    ALTER TABLE collector_runs
    ADD COLUMN IF NOT EXISTS normalized_loadouts INT NOT NULL DEFAULT 0
    """,
]


async def apply_schema(conn: psycopg.AsyncConnection) -> None:
    async with conn.transaction():
        for stmt in DDL_STATEMENTS:
            await conn.execute(stmt)
    logger.info("Database schema applied (%s statements).", len(DDL_STATEMENTS))
