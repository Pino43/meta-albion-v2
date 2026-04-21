"""Persist normalized loadouts derived from kill_events.raw_json."""

from __future__ import annotations

import json
import logging
from typing import Any

import psycopg

from albion_analytics.analysis.loadouts import (
    LOADOUT_EXTRACTOR_VERSION,
    EventLoadout,
    extract_event_loadouts,
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


def _loadout_params(row: EventLoadout) -> tuple[Any, ...]:
    return (
        row.source_region,
        row.event_id,
        row.perspective,
        row.participant_index,
        row.time_stamp,
        row.patch_id,
        row.battle_id,
        row.kill_area,
        row.player_id,
        row.player_name,
        row.guild_id,
        row.guild_name,
        row.alliance_id,
        row.alliance_name,
        row.average_item_power,
        row.number_of_participants,
        row.group_member_count,
        row.total_victim_kill_fame,
        row.kill_fame,
        row.death_fame,
        row.damage_done,
        row.support_healing_done,
        row.fame_ratio,
        row.build_key,
        row.slots["main_hand_type"],
        row.slots["off_hand_type"],
        row.slots["head_type"],
        row.slots["armor_type"],
        row.slots["shoes_type"],
        row.slots["bag_type"],
        row.slots["cape_type"],
        row.slots["mount_type"],
        row.slots["potion_type"],
        row.slots["food_type"],
    )


async def upsert_event_loadouts(
    conn: psycopg.AsyncConnection,
    rows: list[EventLoadout],
) -> int:
    """Upsert normalized loadout rows and return affected row count."""
    if not rows:
        return 0

    sql = """
    INSERT INTO event_loadouts (
      source_region,
      event_id,
      perspective,
      participant_index,
      time_stamp,
      patch_id,
      battle_id,
      kill_area,
      player_id,
      player_name,
      guild_id,
      guild_name,
      alliance_id,
      alliance_name,
      average_item_power,
      number_of_participants,
      group_member_count,
      total_victim_kill_fame,
      kill_fame,
      death_fame,
      damage_done,
      support_healing_done,
      fame_ratio,
      build_key,
      main_hand_type,
      off_hand_type,
      head_type,
      armor_type,
      shoes_type,
      bag_type,
      cape_type,
      mount_type,
      potion_type,
      food_type
    )
    VALUES (
      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
      %s, %s, %s, %s
    )
    ON CONFLICT (source_region, event_id, perspective, participant_index) DO UPDATE SET
      time_stamp = EXCLUDED.time_stamp,
      patch_id = EXCLUDED.patch_id,
      battle_id = EXCLUDED.battle_id,
      kill_area = EXCLUDED.kill_area,
      player_id = EXCLUDED.player_id,
      player_name = EXCLUDED.player_name,
      guild_id = EXCLUDED.guild_id,
      guild_name = EXCLUDED.guild_name,
      alliance_id = EXCLUDED.alliance_id,
      alliance_name = EXCLUDED.alliance_name,
      average_item_power = EXCLUDED.average_item_power,
      number_of_participants = EXCLUDED.number_of_participants,
      group_member_count = EXCLUDED.group_member_count,
      total_victim_kill_fame = EXCLUDED.total_victim_kill_fame,
      kill_fame = EXCLUDED.kill_fame,
      death_fame = EXCLUDED.death_fame,
      damage_done = EXCLUDED.damage_done,
      support_healing_done = EXCLUDED.support_healing_done,
      fame_ratio = EXCLUDED.fame_ratio,
      build_key = EXCLUDED.build_key,
      main_hand_type = EXCLUDED.main_hand_type,
      off_hand_type = EXCLUDED.off_hand_type,
      head_type = EXCLUDED.head_type,
      armor_type = EXCLUDED.armor_type,
      shoes_type = EXCLUDED.shoes_type,
      bag_type = EXCLUDED.bag_type,
      cape_type = EXCLUDED.cape_type,
      mount_type = EXCLUDED.mount_type,
      potion_type = EXCLUDED.potion_type,
      food_type = EXCLUDED.food_type
    """
    async with conn.transaction():
        async with conn.cursor() as cur:
            await cur.executemany(sql, [_loadout_params(row) for row in rows])
            return len(rows)


async def normalize_pending_event_loadouts(
    conn: psycopg.AsyncConnection,
    *,
    limit: int,
) -> int:
    """Normalize kill_events rows not yet represented in event_loadouts."""
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT ke.source_region, ke.event_id, ke.time_stamp, ke.patch_id, ke.raw_json
            FROM kill_events ke
            LEFT JOIN event_loadout_normalization_status status
              ON status.source_region = ke.source_region
             AND status.event_id = ke.event_id
            WHERE status.event_id IS NULL
               OR status.extractor_version < %s
            ORDER BY ke.time_stamp ASC
            LIMIT %s
            """,
            (LOADOUT_EXTRACTOR_VERSION, limit),
        )
        events = await cur.fetchall()

    rows: list[EventLoadout] = []
    event_keys: list[tuple[str, int]] = []
    statuses: list[tuple[str, int, int, int, str | None]] = []
    for source_region, event_id, time_stamp, patch_id, raw_json in events:
        event_keys.append((source_region, int(event_id)))
        raw_event = _raw_json_as_dict(raw_json)
        if raw_event is None:
            statuses.append(
                (
                    source_region,
                    int(event_id),
                    0,
                    LOADOUT_EXTRACTOR_VERSION,
                    "invalid_raw_json",
                )
            )
            continue
        event_rows = extract_event_loadouts(
            source_region=source_region,
            event_id=int(event_id),
            time_stamp=time_stamp,
            patch_id=patch_id,
            raw_event=raw_event,
        )
        rows.extend(event_rows)
        statuses.append(
            (
                source_region,
                int(event_id),
                len(event_rows),
                LOADOUT_EXTRACTOR_VERSION,
                None,
            )
        )

    await delete_event_loadouts(conn, event_keys)
    upserted = await upsert_event_loadouts(conn, rows)
    await mark_event_loadouts_normalized(conn, statuses)
    logger.info(
        "normalized_loadouts events=%s rows=%s upserted=%s skipped_invalid_raw=%s",
        len(events),
        len(rows),
        upserted,
        sum(1 for _, _, row_count, _, reason in statuses if row_count == 0 and reason),
    )
    return upserted


async def delete_event_loadouts(
    conn: psycopg.AsyncConnection,
    event_keys: list[tuple[str, int]],
) -> None:
    if not event_keys:
        return
    async with conn.transaction():
        async with conn.cursor() as cur:
            await cur.executemany(
                """
                DELETE FROM event_loadouts
                WHERE source_region = %s
                  AND event_id = %s
                """,
                event_keys,
            )


async def mark_event_loadouts_normalized(
    conn: psycopg.AsyncConnection,
    statuses: list[tuple[str, int, int, int, str | None]],
) -> None:
    if not statuses:
        return
    async with conn.transaction():
        async with conn.cursor() as cur:
            await cur.executemany(
                """
                INSERT INTO event_loadout_normalization_status (
                  source_region,
                  event_id,
                  normalized_at,
                  row_count,
                  extractor_version,
                  skipped_reason
                )
                VALUES (%s, %s, NOW(), %s, %s, %s)
                ON CONFLICT (source_region, event_id) DO UPDATE SET
                  normalized_at = EXCLUDED.normalized_at,
                  row_count = EXCLUDED.row_count,
                  extractor_version = EXCLUDED.extractor_version,
                  skipped_reason = EXCLUDED.skipped_reason
                """,
                statuses,
            )


async def count_pending_event_loadouts(conn: psycopg.AsyncConnection) -> int:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT count(*)
            FROM kill_events ke
            LEFT JOIN event_loadout_normalization_status status
              ON status.source_region = ke.source_region
             AND status.event_id = ke.event_id
            WHERE status.event_id IS NULL
               OR status.extractor_version < %s
            """,
            (LOADOUT_EXTRACTOR_VERSION,),
        )
        row = await cur.fetchone()
    return int(row[0]) if row else 0
