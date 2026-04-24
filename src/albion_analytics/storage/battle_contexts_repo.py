"""Persist compact Gameinfo battle summaries and apply fight-scale enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psycopg


@dataclass(frozen=True)
class BattleRef:
    source_region: str
    battle_id: int


@dataclass(frozen=True)
class BattleContext:
    source_region: str
    battle_id: int
    start_time: datetime | None
    end_time: datetime | None
    total_fame: int | None
    total_kills: int | None
    player_count: int
    cluster_name: str | None


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def battle_player_count(payload: dict[str, Any]) -> int:
    players = payload.get("players")
    if isinstance(players, dict):
        return len(players)
    if isinstance(players, list):
        return len(players)
    return 0


def parse_battle_context(
    *,
    source_region: str,
    payload: dict[str, Any],
) -> BattleContext | None:
    battle_id = _as_int(payload.get("id"))
    if battle_id is None:
        return None

    return BattleContext(
        source_region=source_region,
        battle_id=battle_id,
        start_time=_parse_ts(payload.get("startTime")),
        end_time=_parse_ts(payload.get("endTime")),
        total_fame=_as_int(payload.get("totalFame")),
        total_kills=_as_int(payload.get("totalKills")),
        player_count=battle_player_count(payload),
        cluster_name=_as_str(payload.get("clusterName")),
    )


async def fetch_pending_battle_refs(
    conn: psycopg.AsyncConnection,
    *,
    limit: int,
) -> list[BattleRef]:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            WITH valid_events AS (
              SELECT
                source_region,
                (raw_json->>'BattleId')::bigint AS battle_id,
                time_stamp
              FROM kill_events
              WHERE NULLIF(raw_json->>'BattleId', '') ~ '^[0-9]+$'
            ),
            candidates AS (
              SELECT
                ve.source_region,
                ve.battle_id,
                max(ve.time_stamp) AS latest_event_at
              FROM valid_events ve
              LEFT JOIN battle_contexts bc
                ON bc.source_region = ve.source_region
               AND bc.battle_id = ve.battle_id
              WHERE bc.battle_id IS NULL
              GROUP BY ve.source_region, ve.battle_id
            )
            SELECT source_region, battle_id
            FROM candidates
            ORDER BY latest_event_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = await cur.fetchall()
    return [BattleRef(source_region=row[0], battle_id=int(row[1])) for row in rows]


async def upsert_battle_contexts(
    conn: psycopg.AsyncConnection,
    rows: list[BattleContext],
) -> int:
    if not rows:
        return 0

    sql = """
    INSERT INTO battle_contexts (
      source_region,
      battle_id,
      start_time,
      end_time,
      total_fame,
      total_kills,
      player_count,
      cluster_name,
      fetched_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (source_region, battle_id) DO UPDATE SET
      start_time = EXCLUDED.start_time,
      end_time = EXCLUDED.end_time,
      total_fame = EXCLUDED.total_fame,
      total_kills = EXCLUDED.total_kills,
      player_count = EXCLUDED.player_count,
      cluster_name = EXCLUDED.cluster_name,
      fetched_at = EXCLUDED.fetched_at
    """
    params = [
        (
            row.source_region,
            row.battle_id,
            row.start_time,
            row.end_time,
            row.total_fame,
            row.total_kills,
            row.player_count,
            row.cluster_name,
        )
        for row in rows
    ]
    async with conn.transaction():
        async with conn.cursor() as cur:
            await cur.executemany(sql, params)
    return len(rows)


async def apply_battle_contexts_to_event_contexts(conn: psycopg.AsyncConnection) -> int:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            WITH valid_events AS (
              SELECT
                source_region,
                event_id,
                (raw_json->>'BattleId')::bigint AS battle_id
              FROM kill_events
              WHERE NULLIF(raw_json->>'BattleId', '') ~ '^[0-9]+$'
            ),
            event_battles AS (
              SELECT
                ec.source_region,
                ec.event_id,
                bc.player_count,
                CASE
                  WHEN bc.player_count <= 0 THEN 'unknown'
                  WHEN bc.player_count = 1 THEN 'solo'
                  WHEN bc.player_count = 2 THEN 'duo'
                  WHEN bc.player_count <= 5 THEN 'small_party'
                  WHEN bc.player_count <= 10 THEN 'party'
                  WHEN bc.player_count <= 20 THEN 'large_party'
                  ELSE 'zvz'
                END AS fight_scale_bucket
              FROM event_contexts ec
              JOIN valid_events ve
                ON ve.source_region = ec.source_region
               AND ve.event_id = ec.event_id
              JOIN battle_contexts bc
                ON bc.source_region = ve.source_region
               AND bc.battle_id = ve.battle_id
            )
            UPDATE event_contexts ec
            SET
              battle_player_count = eb.player_count,
              fight_scale_bucket = eb.fight_scale_bucket,
              scale_source = 'battle_players',
              classified_at = NOW()
            FROM event_battles eb
            WHERE ec.source_region = eb.source_region
              AND ec.event_id = eb.event_id
              AND (
                ec.battle_player_count IS DISTINCT FROM eb.player_count
                OR ec.fight_scale_bucket IS DISTINCT FROM eb.fight_scale_bucket
                OR ec.scale_source IS DISTINCT FROM 'battle_players'
              )
            """
        )
        updated = cur.rowcount or 0
    await conn.commit()
    return updated
