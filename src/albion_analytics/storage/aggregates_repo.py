"""Daily aggregate tables for ranking queries."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import psycopg

logger = logging.getLogger(__name__)

SLOT_TO_COLUMN: dict[str, str] = {
    "main_hand": "main_hand_type",
    "off_hand": "off_hand_type",
    "head": "head_type",
    "armor": "armor_type",
    "shoes": "shoes_type",
    "bag": "bag_type",
    "cape": "cape_type",
    "mount": "mount_type",
    "potion": "potion_type",
    "food": "food_type",
}


@dataclass(frozen=True)
class DailyAggregateResult:
    item_rows: int
    build_rows: int


def utc_day_lower_bound(days: int, *, now: datetime | None = None) -> date:
    """Return the first UTC day included in a recent-N-days query."""
    if days < 1:
        raise ValueError("days must be >= 1")
    ref = now or datetime.now(UTC)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    return ref.astimezone(UTC).date() - timedelta(days=days - 1)


def build_item_usage_aggregate_sql(slot: str) -> str:
    column = SLOT_TO_COLUMN[slot]
    return f"""
    INSERT INTO daily_item_usage (
      day,
      source_region,
      perspective,
      slot,
      item_type,
      uses,
      events,
      avg_item_power,
      avg_participants,
      total_kill_fame,
      updated_at
    )
    SELECT
      (time_stamp AT TIME ZONE 'UTC')::date AS day,
      source_region,
      perspective,
      %s AS slot,
      {column} AS item_type,
      count(*) AS uses,
      count(DISTINCT (source_region, event_id)) AS events,
      avg(average_item_power) AS avg_item_power,
      avg(number_of_participants) AS avg_participants,
      sum(COALESCE(kill_fame, total_victim_kill_fame, 0)) AS total_kill_fame,
      NOW() AS updated_at
    FROM event_loadouts
    WHERE time_stamp >= (%s::date::timestamp AT TIME ZONE 'UTC')
      AND {column} IS NOT NULL
      AND {column} <> ''
    GROUP BY day, source_region, perspective, item_type
    ON CONFLICT (day, source_region, perspective, slot, item_type) DO UPDATE SET
      uses = EXCLUDED.uses,
      events = EXCLUDED.events,
      avg_item_power = EXCLUDED.avg_item_power,
      avg_participants = EXCLUDED.avg_participants,
      total_kill_fame = EXCLUDED.total_kill_fame,
      updated_at = EXCLUDED.updated_at
    WHERE (
      daily_item_usage.uses,
      daily_item_usage.events,
      daily_item_usage.avg_item_power,
      daily_item_usage.avg_participants,
      daily_item_usage.total_kill_fame
    ) IS DISTINCT FROM (
      EXCLUDED.uses,
      EXCLUDED.events,
      EXCLUDED.avg_item_power,
      EXCLUDED.avg_participants,
      EXCLUDED.total_kill_fame
    )
    """


def build_build_usage_aggregate_sql() -> str:
    return """
    INSERT INTO daily_build_usage (
      day,
      source_region,
      perspective,
      build_key,
      uses,
      events,
      avg_item_power,
      avg_participants,
      total_kill_fame,
      updated_at
    )
    SELECT
      (time_stamp AT TIME ZONE 'UTC')::date AS day,
      source_region,
      perspective,
      build_key,
      count(*) AS uses,
      count(DISTINCT (source_region, event_id)) AS events,
      avg(average_item_power) AS avg_item_power,
      avg(number_of_participants) AS avg_participants,
      sum(COALESCE(kill_fame, total_victim_kill_fame, 0)) AS total_kill_fame,
      NOW() AS updated_at
    FROM event_loadouts
    WHERE time_stamp >= (%s::date::timestamp AT TIME ZONE 'UTC')
      AND build_key IS NOT NULL
      AND build_key <> ''
    GROUP BY day, source_region, perspective, build_key
    ON CONFLICT (day, source_region, perspective, build_key) DO UPDATE SET
      uses = EXCLUDED.uses,
      events = EXCLUDED.events,
      avg_item_power = EXCLUDED.avg_item_power,
      avg_participants = EXCLUDED.avg_participants,
      total_kill_fame = EXCLUDED.total_kill_fame,
      updated_at = EXCLUDED.updated_at
    WHERE (
      daily_build_usage.uses,
      daily_build_usage.events,
      daily_build_usage.avg_item_power,
      daily_build_usage.avg_participants,
      daily_build_usage.total_kill_fame
    ) IS DISTINCT FROM (
      EXCLUDED.uses,
      EXCLUDED.events,
      EXCLUDED.avg_item_power,
      EXCLUDED.avg_participants,
      EXCLUDED.total_kill_fame
    )
    """


def build_ranking_items_sql(*, region: str | None) -> str:
    where = ["perspective = %s", "slot = %s", "day >= %s"]
    if region:
        where.append("source_region = %s")
    return f"""
    SELECT
      item_type,
      sum(uses) AS uses,
      sum(events) AS events,
      avg(avg_item_power) AS avg_item_power,
      avg(avg_participants) AS avg_participants,
      sum(total_kill_fame) AS total_kill_fame
    FROM daily_item_usage
    WHERE {" AND ".join(where)}
    GROUP BY item_type
    ORDER BY uses DESC
    LIMIT %s
    """


def build_ranking_builds_sql(*, region: str | None) -> str:
    where = ["perspective = %s", "day >= %s"]
    if region:
        where.append("source_region = %s")
    return f"""
    SELECT
      build_key,
      sum(uses) AS uses,
      sum(events) AS events,
      avg(avg_item_power) AS avg_item_power,
      avg(avg_participants) AS avg_participants,
      sum(total_kill_fame) AS total_kill_fame
    FROM daily_build_usage
    WHERE {" AND ".join(where)}
    GROUP BY build_key
    ORDER BY uses DESC
    LIMIT %s
    """


async def aggregate_daily_usage(
    conn: psycopg.AsyncConnection,
    *,
    lookback_days: int,
) -> DailyAggregateResult:
    lower_day = utc_day_lower_bound(lookback_days)
    item_rows = 0
    build_rows = 0
    async with conn.transaction():
        async with conn.cursor() as cur:
            for slot in SLOT_TO_COLUMN:
                await cur.execute(build_item_usage_aggregate_sql(slot), (slot, lower_day))
                item_rows += cur.rowcount or 0
            await cur.execute(build_build_usage_aggregate_sql(), (lower_day,))
            build_rows = cur.rowcount or 0

    logger.info(
        "daily_aggregates lookback_days=%s item_rows=%s build_rows=%s",
        lookback_days,
        item_rows,
        build_rows,
    )
    return DailyAggregateResult(item_rows=item_rows, build_rows=build_rows)


async def fetch_item_rankings(
    conn: psycopg.AsyncConnection,
    *,
    slot: str,
    perspective: str,
    days: int,
    region: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    lower_day = utc_day_lower_bound(days)
    params: list[Any] = [perspective, slot, lower_day]
    if region:
        params.append(region)
    params.append(limit)

    async with conn.cursor() as cur:
        await cur.execute(build_ranking_items_sql(region=region), params)
        rows = await cur.fetchall()

    return [
        {
            "item_type": row[0],
            "uses": row[1],
            "events": row[2],
            "avg_item_power": float(row[3]) if row[3] is not None else None,
            "avg_participants": float(row[4]) if row[4] is not None else None,
            "total_kill_fame": row[5],
        }
        for row in rows
    ]


async def fetch_build_rankings(
    conn: psycopg.AsyncConnection,
    *,
    perspective: str,
    days: int,
    region: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    lower_day = utc_day_lower_bound(days)
    params: list[Any] = [perspective, lower_day]
    if region:
        params.append(region)
    params.append(limit)

    async with conn.cursor() as cur:
        await cur.execute(build_ranking_builds_sql(region=region), params)
        rows = await cur.fetchall()

    return [
        {
            "build_key": row[0],
            "uses": row[1],
            "events": row[2],
            "avg_item_power": float(row[3]) if row[3] is not None else None,
            "avg_participants": float(row[4]) if row[4] is not None else None,
            "total_kill_fame": row[5],
        }
        for row in rows
    ]
