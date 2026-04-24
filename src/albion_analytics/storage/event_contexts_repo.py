"""Persist and refresh derived event context classifications."""

from __future__ import annotations

import json
import logging
from typing import Any

import psycopg

from albion_analytics.analysis.event_contexts import (
    EVENT_CONTEXT_CLASSIFIER_VERSION,
    EventContext,
    build_event_context,
)

logger = logging.getLogger(__name__)


def _raw_json_as_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _context_params(row: EventContext) -> tuple[Any, ...]:
    return (
        row.source_region,
        row.event_id,
        row.time_stamp,
        row.kill_area_raw,
        row.kill_area_slug,
        row.content_type,
        row.fight_scale_bucket,
        row.reported_participant_count,
        row.observed_kill_side_count,
        row.battle_player_count,
        row.scale_source,
        row.classifier_version,
    )


async def upsert_event_contexts(
    conn: psycopg.AsyncConnection,
    rows: list[EventContext],
) -> int:
    if not rows:
        return 0

    sql = """
    INSERT INTO event_contexts (
      source_region,
      event_id,
      time_stamp,
      kill_area_raw,
      kill_area_slug,
      content_type,
      fight_scale_bucket,
      reported_participant_count,
      observed_kill_side_count,
      battle_player_count,
      scale_source,
      classifier_version,
      classified_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (source_region, event_id) DO UPDATE SET
      time_stamp = EXCLUDED.time_stamp,
      kill_area_raw = EXCLUDED.kill_area_raw,
      kill_area_slug = EXCLUDED.kill_area_slug,
      content_type = EXCLUDED.content_type,
      fight_scale_bucket = EXCLUDED.fight_scale_bucket,
      reported_participant_count = EXCLUDED.reported_participant_count,
      observed_kill_side_count = EXCLUDED.observed_kill_side_count,
      battle_player_count = EXCLUDED.battle_player_count,
      scale_source = EXCLUDED.scale_source,
      classifier_version = EXCLUDED.classifier_version,
      classified_at = EXCLUDED.classified_at
    """
    async with conn.transaction():
        async with conn.cursor() as cur:
            await cur.executemany(sql, [_context_params(row) for row in rows])
            return len(rows)


async def classify_pending_event_contexts(
    conn: psycopg.AsyncConnection,
    *,
    limit: int,
) -> int:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT ke.source_region, ke.event_id, ke.time_stamp, ke.raw_json
            FROM kill_events ke
            LEFT JOIN event_contexts ctx
              ON ctx.source_region = ke.source_region
             AND ctx.event_id = ke.event_id
            WHERE ctx.event_id IS NULL
               OR ctx.classifier_version < %s
            ORDER BY ke.time_stamp ASC
            LIMIT %s
            """,
            (EVENT_CONTEXT_CLASSIFIER_VERSION, limit),
        )
        events = await cur.fetchall()

    rows: list[EventContext] = []
    skipped_invalid = 0
    for source_region, event_id, time_stamp, raw_json in events:
        raw_event = _raw_json_as_dict(raw_json)
        if raw_event is None:
            skipped_invalid += 1
            continue
        rows.append(
            build_event_context(
                source_region=source_region,
                event_id=int(event_id),
                time_stamp=time_stamp,
                raw_event=raw_event,
            )
        )

    upserted = await upsert_event_contexts(conn, rows)
    logger.info(
        "classified_event_contexts events=%s upserted=%s skipped_invalid_raw=%s",
        len(events),
        upserted,
        skipped_invalid,
    )
    return upserted


async def count_pending_event_contexts(conn: psycopg.AsyncConnection) -> int:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT count(*)
            FROM kill_events ke
            LEFT JOIN event_contexts ctx
              ON ctx.source_region = ke.source_region
             AND ctx.event_id = ke.event_id
            WHERE ctx.event_id IS NULL
               OR ctx.classifier_version < %s
            """,
            (EVENT_CONTEXT_CLASSIFIER_VERSION,),
        )
        row = await cur.fetchone()
    return int(row[0]) if row else 0
