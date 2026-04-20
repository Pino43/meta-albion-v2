"""Insert kill events with deduplication (Postgres ON CONFLICT)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

import psycopg
from psycopg.types.json import Json

logger = logging.getLogger(__name__)


@dataclass
class EventIngestionResult:
    region: str
    fetched: int
    inserted: int
    skipped_invalid: int


@dataclass(frozen=True)
class NormalizedRawEvent:
    event_id: int
    time_stamp: datetime
    api_payload_version: int | None
    raw_json: dict[str, Any]


RunStatus = Literal["running", "success", "failed"]


def _parse_int(raw: Any) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        value = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _normalize_raw_event(item: Any) -> NormalizedRawEvent | None:
    if not isinstance(item, dict):
        return None

    event_id = _parse_int(item.get("EventId"))
    ts_raw = item.get("TimeStamp")
    if event_id is None or not isinstance(ts_raw, str):
        return None

    time_stamp = _parse_ts(ts_raw)
    if time_stamp is None:
        return None

    return NormalizedRawEvent(
        event_id=event_id,
        time_stamp=time_stamp,
        api_payload_version=_parse_int(item.get("Version")),
        raw_json=item,
    )


async def start_collector_run(conn: psycopg.AsyncConnection) -> int:
    """Create a collector run row and return its id."""
    async with conn.transaction():
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO collector_runs (status)
                VALUES ('running')
                RETURNING id
                """
            )
            row = await cur.fetchone()
    if row is None:
        raise RuntimeError("collector_runs insert did not return an id")
    return int(row[0])


async def finish_collector_run(
    conn: psycopg.AsyncConnection,
    run_id: int,
    *,
    status: RunStatus,
    total_fetched: int = 0,
    total_inserted: int = 0,
    total_skipped_invalid: int = 0,
    patch_rows_updated: int = 0,
    normalized_loadouts: int = 0,
    error_message: str | None = None,
) -> None:
    """Mark a collector run as finished."""
    if error_message is not None:
        error_message = error_message[:4000]
    async with conn.transaction():
        await conn.execute(
            """
            UPDATE collector_runs
            SET
              finished_at = NOW(),
              status = %s,
              total_fetched = %s,
              total_inserted = %s,
              total_skipped_invalid = %s,
              patch_rows_updated = %s,
              normalized_loadouts = %s,
              error_message = %s
            WHERE id = %s
            """,
            (
                status,
                total_fetched,
                total_inserted,
                total_skipped_invalid,
                patch_rows_updated,
                normalized_loadouts,
                error_message,
                run_id,
            ),
        )


async def upsert_raw_events(
    conn: psycopg.AsyncConnection,
    source_region: str,
    raw_events: list[dict[str, Any]],
) -> EventIngestionResult:
    """
    Insert events; duplicates on (source_region, event_id) are ignored.

    Invalid rows (missing/invalid id or timestamp) are skipped.
    """
    inserted = 0
    skipped = 0
    max_event_id: int | None = None
    sql = """
    INSERT INTO kill_events (source_region, event_id, time_stamp, api_payload_version, raw_json)
    VALUES (%s, %s, %s, %s, %s::jsonb)
    ON CONFLICT (source_region, event_id) DO NOTHING
    """
    async with conn.transaction():
        async with conn.cursor() as cur:
            for item in raw_events:
                normalized = _normalize_raw_event(item)
                if normalized is None:
                    skipped += 1
                    continue

                if max_event_id is None or normalized.event_id > max_event_id:
                    max_event_id = normalized.event_id

                await cur.execute(
                    sql,
                    (
                        source_region,
                        normalized.event_id,
                        normalized.time_stamp,
                        normalized.api_payload_version,
                        Json(normalized.raw_json),
                    ),
                )
                if cur.rowcount:
                    inserted += cur.rowcount

        if max_event_id is not None:
            await conn.execute(
                """
                INSERT INTO ingestion_cursors (source_region, last_max_event_id, last_poll_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (source_region) DO UPDATE SET
                  last_max_event_id = GREATEST(
                    COALESCE(ingestion_cursors.last_max_event_id, 0),
                    COALESCE(EXCLUDED.last_max_event_id, 0)
                  ),
                  last_poll_at = EXCLUDED.last_poll_at
                """,
                (source_region, max_event_id),
            )

    return EventIngestionResult(
        region=source_region,
        fetched=len(raw_events),
        inserted=inserted,
        skipped_invalid=skipped,
    )


async def get_last_event_id(conn: psycopg.AsyncConnection, region: str) -> int | None:
    """Return the last seen event id for a region, or None if no cursor exists."""
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT last_max_event_id FROM ingestion_cursors WHERE source_region = %s",
            (region,),
        )
        row = await cur.fetchone()
        return row[0] if row else None


async def assign_patches_from_ranges(conn: psycopg.AsyncConnection) -> int:
    """
    Fill patch_id for rows where time_stamp falls in [starts_at, ends_at).

    Keep game_patches ranges non-overlapping so each event maps to at most one patch.
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """
            UPDATE kill_events ke
            SET patch_id = gp.id
            FROM game_patches gp
            WHERE ke.patch_id IS NULL
              AND ke.time_stamp >= gp.starts_at
              AND (gp.ends_at IS NULL OR ke.time_stamp < gp.ends_at)
            """
        )
        n = cur.rowcount
    await conn.commit()
    logger.info("Assigned patch_id on %s rows", n)
    return n
