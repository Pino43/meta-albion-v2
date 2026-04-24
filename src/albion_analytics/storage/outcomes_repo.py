"""Outcome aggregates and product-facing leaderboard/detail queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import psycopg

from albion_analytics.analysis.event_contexts import normalize_kill_area_slug
from albion_analytics.storage.aggregates_repo import SLOT_TO_COLUMN, utc_day_lower_bound

SMOOTHING_PRIOR_WEIGHT = 25.0
BUILD_KEY_COMPONENTS: tuple[str, ...] = (
    "head_type",
    "armor_type",
    "shoes_type",
    "main_hand_type",
    "off_hand_type",
    "cape_type",
)
BUILD_KEY_SLOT_INDEX: dict[str, int] = {
    "head": 0,
    "armor": 1,
    "shoes": 2,
    "main_hand": 3,
    "off_hand": 4,
    "cape": 5,
}


def item_family_key(item_type: str) -> str:
    base = item_type.split("@", 1)[0]
    parts = base.split("_", 1)
    if len(parts) == 2 and parts[0].startswith("T") and parts[0][1:].isdigit():
        return parts[1]
    return base


@dataclass(frozen=True)
class OutcomeAggregateResult:
    item_rows: int
    build_rows: int


def build_item_outcome_aggregate_sql(slot: str) -> str:
    column = SLOT_TO_COLUMN[slot]
    return f"""
    INSERT INTO daily_item_outcomes (
      day,
      source_region,
      patch_id,
      content_type,
      fight_scale_bucket,
      slot,
      item_type,
      kill_credit,
      death_count,
      appearance_count,
      event_count,
      avg_item_power,
      total_kill_fame,
      updated_at
    )
    SELECT
      (el.time_stamp AT TIME ZONE 'UTC')::date AS day,
      el.source_region,
      COALESCE(el.patch_id, 0) AS patch_id,
      ec.content_type,
      ec.fight_scale_bucket,
      %s AS slot,
      {column} AS item_type,
      SUM(
        CASE
          WHEN el.perspective = 'victim' THEN 0.0
          ELSE 1.0 / GREATEST(ec.observed_kill_side_count, 1)
        END
      ) AS kill_credit,
      SUM(CASE WHEN el.perspective = 'victim' THEN 1.0 ELSE 0.0 END) AS death_count,
      COUNT(*) AS appearance_count,
      COUNT(DISTINCT (el.source_region, el.event_id)) AS event_count,
      AVG(el.average_item_power) AS avg_item_power,
      SUM(COALESCE(el.kill_fame, el.total_victim_kill_fame, 0)) AS total_kill_fame,
      NOW() AS updated_at
    FROM event_loadouts el
    JOIN event_contexts ec
      ON ec.source_region = el.source_region
     AND ec.event_id = el.event_id
    WHERE el.time_stamp >= (%s::date::timestamp AT TIME ZONE 'UTC')
      AND {column} IS NOT NULL
      AND {column} <> ''
    GROUP BY
      day,
      el.source_region,
      COALESCE(el.patch_id, 0),
      ec.content_type,
      ec.fight_scale_bucket,
      item_type
    ON CONFLICT (
      day,
      source_region,
      patch_id,
      content_type,
      fight_scale_bucket,
      slot,
      item_type
    ) DO UPDATE SET
      kill_credit = EXCLUDED.kill_credit,
      death_count = EXCLUDED.death_count,
      appearance_count = EXCLUDED.appearance_count,
      event_count = EXCLUDED.event_count,
      avg_item_power = EXCLUDED.avg_item_power,
      total_kill_fame = EXCLUDED.total_kill_fame,
      updated_at = EXCLUDED.updated_at
    WHERE (
      daily_item_outcomes.kill_credit,
      daily_item_outcomes.death_count,
      daily_item_outcomes.appearance_count,
      daily_item_outcomes.event_count,
      daily_item_outcomes.avg_item_power,
      daily_item_outcomes.total_kill_fame
    ) IS DISTINCT FROM (
      EXCLUDED.kill_credit,
      EXCLUDED.death_count,
      EXCLUDED.appearance_count,
      EXCLUDED.event_count,
      EXCLUDED.avg_item_power,
      EXCLUDED.total_kill_fame
    )
    """


def build_build_outcome_aggregate_sql() -> str:
    return """
    INSERT INTO daily_build_outcomes (
      day,
      source_region,
      patch_id,
      content_type,
      fight_scale_bucket,
      build_key,
      kill_credit,
      death_count,
      appearance_count,
      event_count,
      avg_item_power,
      total_kill_fame,
      updated_at
    )
    SELECT
      (el.time_stamp AT TIME ZONE 'UTC')::date AS day,
      el.source_region,
      COALESCE(el.patch_id, 0) AS patch_id,
      ec.content_type,
      ec.fight_scale_bucket,
      el.build_key,
      SUM(
        CASE
          WHEN el.perspective = 'victim' THEN 0.0
          ELSE 1.0 / GREATEST(ec.observed_kill_side_count, 1)
        END
      ) AS kill_credit,
      SUM(CASE WHEN el.perspective = 'victim' THEN 1.0 ELSE 0.0 END) AS death_count,
      COUNT(*) AS appearance_count,
      COUNT(DISTINCT (el.source_region, el.event_id)) AS event_count,
      AVG(el.average_item_power) AS avg_item_power,
      SUM(COALESCE(el.kill_fame, el.total_victim_kill_fame, 0)) AS total_kill_fame,
      NOW() AS updated_at
    FROM event_loadouts el
    JOIN event_contexts ec
      ON ec.source_region = el.source_region
     AND ec.event_id = el.event_id
    WHERE el.time_stamp >= (%s::date::timestamp AT TIME ZONE 'UTC')
      AND el.build_key IS NOT NULL
      AND el.build_key <> ''
    GROUP BY
      day,
      el.source_region,
      COALESCE(el.patch_id, 0),
      ec.content_type,
      ec.fight_scale_bucket,
      el.build_key
    ON CONFLICT (
      day,
      source_region,
      patch_id,
      content_type,
      fight_scale_bucket,
      build_key
    ) DO UPDATE SET
      kill_credit = EXCLUDED.kill_credit,
      death_count = EXCLUDED.death_count,
      appearance_count = EXCLUDED.appearance_count,
      event_count = EXCLUDED.event_count,
      avg_item_power = EXCLUDED.avg_item_power,
      total_kill_fame = EXCLUDED.total_kill_fame,
      updated_at = EXCLUDED.updated_at
    WHERE (
      daily_build_outcomes.kill_credit,
      daily_build_outcomes.death_count,
      daily_build_outcomes.appearance_count,
      daily_build_outcomes.event_count,
      daily_build_outcomes.avg_item_power,
      daily_build_outcomes.total_kill_fame
    ) IS DISTINCT FROM (
      EXCLUDED.kill_credit,
      EXCLUDED.death_count,
      EXCLUDED.appearance_count,
      EXCLUDED.event_count,
      EXCLUDED.avg_item_power,
      EXCLUDED.total_kill_fame
    )
    """


async def aggregate_daily_outcomes(
    conn: psycopg.AsyncConnection,
    *,
    lookback_days: int,
) -> OutcomeAggregateResult:
    lower_day = utc_day_lower_bound(lookback_days)
    item_rows = 0
    build_rows = 0
    async with conn.transaction():
        async with conn.cursor() as cur:
            for slot in SLOT_TO_COLUMN:
                await cur.execute(build_item_outcome_aggregate_sql(slot), (slot, lower_day))
                item_rows += cur.rowcount or 0
            await cur.execute(build_build_outcome_aggregate_sql(), (lower_day,))
            build_rows = cur.rowcount or 0
    return OutcomeAggregateResult(item_rows=item_rows, build_rows=build_rows)


def parse_build_key(build_key: str) -> dict[str, str | None]:
    parts = build_key.split("|")
    padded = (parts + [""] * len(BUILD_KEY_COMPONENTS))[: len(BUILD_KEY_COMPONENTS)]
    return {
        name: (value or None)
        for name, value in zip(BUILD_KEY_COMPONENTS, padded, strict=True)
    }


def build_key_slot_value(build_key: str, slot: str) -> str | None:
    index = BUILD_KEY_SLOT_INDEX.get(slot)
    if index is None:
        return None
    parts = build_key.split("|")
    if index >= len(parts):
        return None
    value = parts[index]
    return value or None


def _merge_metric_rows(
    rows: list[dict[str, Any]],
    *,
    key_name: str,
    key_value: str,
) -> dict[str, Any]:
    avg_item_power_weight = 0
    avg_item_power_total = 0.0
    for row in rows:
        if row["avg_item_power"] is None:
            continue
        weight = int(row["appearance_count"] or 0)
        avg_item_power_weight += weight
        avg_item_power_total += float(row["avg_item_power"]) * weight

    return {
        key_name: key_value,
        "kill_credit": sum(float(row["kill_credit"] or 0.0) for row in rows),
        "death_count": sum(float(row["death_count"] or 0.0) for row in rows),
        "appearance_count": sum(int(row["appearance_count"] or 0) for row in rows),
        "event_count": sum(int(row["event_count"] or 0) for row in rows),
        "avg_item_power": (
            avg_item_power_total / avg_item_power_weight if avg_item_power_weight > 0 else None
        ),
        "total_kill_fame": sum(int(row["total_kill_fame"] or 0) for row in rows),
    }


def _group_item_rows_by_family(
    item_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in item_rows:
        grouped.setdefault(item_family_key(row["item_type"]), []).append(row)

    family_rows: list[dict[str, Any]] = []
    representative_item_types: dict[str, str] = {}
    for family_key, rows in grouped.items():
        representative = max(
            rows,
            key=lambda row: (
                int(row["appearance_count"] or 0),
                float(row["kill_credit"] or 0.0) + float(row["death_count"] or 0.0),
                row["item_type"],
            ),
        )
        representative_item_types[family_key] = representative["item_type"]
        family_rows.append(
            {
                **_merge_metric_rows(rows, key_name="family_key", key_value=family_key),
                "variant_count": len(rows),
                "representative_item_type": representative["item_type"],
            }
        )

    return family_rows, representative_item_types


def _coerce_metric_row(row: tuple[Any, ...], key_name: str) -> dict[str, Any]:
    return {
        key_name: row[0],
        "kill_credit": float(row[1] or 0.0),
        "death_count": float(row[2] or 0.0),
        "appearance_count": int(row[3] or 0),
        "event_count": int(row[4] or 0),
        "avg_item_power": float(row[5]) if row[5] is not None else None,
        "total_kill_fame": int(row[6] or 0),
    }


def _baseline_rate(rows: list[dict[str, Any]]) -> float:
    total_kill_credit = sum(row["kill_credit"] for row in rows)
    total_death_count = sum(row["death_count"] for row in rows)
    total_sample = total_kill_credit + total_death_count
    if total_sample <= 0:
        return 0.5
    return total_kill_credit / total_sample


def _confidence_label(sample: float) -> str:
    if sample < 25:
        return "low"
    if sample < 100:
        return "medium"
    return "high"


def _scored_row(
    row: dict[str, Any],
    *,
    baseline_rate: float,
    total_appearance_count: int,
) -> dict[str, Any]:
    sample = row["kill_credit"] + row["death_count"]
    kill_side_rate = row["kill_credit"] / sample if sample > 0 else 0.0
    kd_ratio = None if row["death_count"] <= 0 else row["kill_credit"] / row["death_count"]
    smoothed_rate = (
        (row["kill_credit"] + (SMOOTHING_PRIOR_WEIGHT * baseline_rate))
        / (sample + SMOOTHING_PRIOR_WEIGHT)
    )
    return {
        **row,
        "kill_side_rate": kill_side_rate,
        "kd_ratio": kd_ratio,
        "sample": sample,
        "pick_rate": (
            row["appearance_count"] / total_appearance_count if total_appearance_count > 0 else 0.0
        ),
        "baseline_rate": baseline_rate,
        "adjusted_score": smoothed_rate - baseline_rate,
        "confidence": _confidence_label(sample),
    }


def _distribution_row(row: dict[str, Any]) -> dict[str, Any]:
    sample = row["kill_credit"] + row["death_count"]
    return {
        **row,
        "kill_side_rate": row["kill_credit"] / sample if sample > 0 else 0.0,
        "kd_ratio": None if row["death_count"] <= 0 else row["kill_credit"] / row["death_count"],
        "sample": sample,
        "confidence": _confidence_label(sample),
    }


def _aggregate_filter_sql(
    *,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
) -> tuple[list[str], list[Any]]:
    clauses = ["day >= %s"]
    params: list[Any] = []
    if region is not None:
        clauses.append("source_region = %s")
        params.append(region)
    if patch_id is not None:
        clauses.append("patch_id = %s")
        params.append(patch_id)
    if content_type is not None:
        clauses.append("content_type = %s")
        params.append(content_type)
    if fight_scale is not None:
        clauses.append("fight_scale_bucket = %s")
        params.append(fight_scale)
    return clauses, params


def _raw_filter_sql(
    *,
    lower_day: date,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    kill_area: str | None,
) -> tuple[list[str], list[Any]]:
    clauses = ["el.time_stamp >= (%s::date::timestamp AT TIME ZONE 'UTC')"]
    params: list[Any] = [lower_day]
    if region is not None:
        clauses.append("el.source_region = %s")
        params.append(region)
    if patch_id is not None:
        clauses.append("COALESCE(el.patch_id, 0) = %s")
        params.append(patch_id)
    if content_type is not None:
        clauses.append("ec.content_type = %s")
        params.append(content_type)
    if fight_scale is not None:
        clauses.append("ec.fight_scale_bucket = %s")
        params.append(fight_scale)
    if kill_area is not None:
        clauses.append("ec.kill_area_slug = %s")
        params.append(normalize_kill_area_slug(kill_area))
    return clauses, params


async def _fetch_grouped_item_rows_from_aggregates(
    conn: psycopg.AsyncConnection,
    *,
    slot: str,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    item_type: str | None = None,
    item_types: list[str] | None = None,
    group_sql: str = "item_type",
    key_name: str = "item_type",
) -> list[dict[str, Any]]:
    lower_day = utc_day_lower_bound(days)
    where, params = _aggregate_filter_sql(
        region=region,
        patch_id=patch_id,
        content_type=content_type,
        fight_scale=fight_scale,
    )
    if item_type is not None:
        where.append("item_type = %s")
        params.append(item_type)
    if item_types is not None:
        where.append("item_type = ANY(%s)")
        params.append(item_types)
    params = [lower_day, *params, slot]
    sql = f"""
    SELECT
      {group_sql} AS group_key,
      SUM(kill_credit) AS kill_credit,
      SUM(death_count) AS death_count,
      SUM(appearance_count) AS appearance_count,
      SUM(event_count) AS event_count,
      AVG(avg_item_power) AS avg_item_power,
      SUM(total_kill_fame) AS total_kill_fame
    FROM daily_item_outcomes
    WHERE {" AND ".join(where)}
      AND slot = %s
    GROUP BY group_key
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
    return [_coerce_metric_row(row, key_name) for row in rows]


async def _fetch_grouped_build_rows_from_aggregates(
    conn: psycopg.AsyncConnection,
    *,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    build_key: str | None = None,
    main_hand_item_type: str | None = None,
    slot_filter: tuple[str, list[str]] | None = None,
    group_sql: str = "build_key",
    key_name: str = "build_key",
) -> list[dict[str, Any]]:
    lower_day = utc_day_lower_bound(days)
    where, params = _aggregate_filter_sql(
        region=region,
        patch_id=patch_id,
        content_type=content_type,
        fight_scale=fight_scale,
    )
    if build_key is not None:
        where.append("build_key = %s")
        params.append(build_key)
    if main_hand_item_type is not None:
        where.append("split_part(build_key, '|', 4) = %s")
        params.append(main_hand_item_type)
    if slot_filter is not None:
        slot, item_types = slot_filter
        index = BUILD_KEY_SLOT_INDEX[slot] + 1
        where.append(f"split_part(build_key, '|', {index}) = ANY(%s)")
        params.append(item_types)
    params = [lower_day, *params]
    sql = f"""
    SELECT
      {group_sql} AS group_key,
      SUM(kill_credit) AS kill_credit,
      SUM(death_count) AS death_count,
      SUM(appearance_count) AS appearance_count,
      SUM(event_count) AS event_count,
      AVG(avg_item_power) AS avg_item_power,
      SUM(total_kill_fame) AS total_kill_fame
    FROM daily_build_outcomes
    WHERE {" AND ".join(where)}
    GROUP BY group_key
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
    return [_coerce_metric_row(row, key_name) for row in rows]


async def _fetch_grouped_item_rows_from_raw(
    conn: psycopg.AsyncConnection,
    *,
    slot: str,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    kill_area: str | None,
    item_type: str | None = None,
    item_types: list[str] | None = None,
    group_sql: str = "item_type",
    key_name: str = "item_type",
) -> list[dict[str, Any]]:
    lower_day = utc_day_lower_bound(days)
    column = SLOT_TO_COLUMN[slot]
    where, params = _raw_filter_sql(
        lower_day=lower_day,
        region=region,
        patch_id=patch_id,
        content_type=content_type,
        fight_scale=fight_scale,
        kill_area=kill_area,
    )
    where.extend([f"el.{column} IS NOT NULL", f"el.{column} <> ''"])
    if item_type is not None:
        where.append(f"el.{column} = %s")
        params.append(item_type)
    if item_types is not None:
        where.append(f"el.{column} = ANY(%s)")
        params.append(item_types)
    selected_group_sql = f"el.{column}" if group_sql == "item_type" else group_sql
    sql = f"""
    SELECT
      {selected_group_sql} AS group_key,
      SUM(
        CASE
          WHEN el.perspective = 'victim' THEN 0.0
          ELSE 1.0 / GREATEST(ec.observed_kill_side_count, 1)
        END
      ) AS kill_credit,
      SUM(CASE WHEN el.perspective = 'victim' THEN 1.0 ELSE 0.0 END) AS death_count,
      COUNT(*) AS appearance_count,
      COUNT(DISTINCT (el.source_region, el.event_id)) AS event_count,
      AVG(el.average_item_power) AS avg_item_power,
      SUM(COALESCE(el.kill_fame, el.total_victim_kill_fame, 0)) AS total_kill_fame
    FROM event_loadouts el
    JOIN event_contexts ec
      ON ec.source_region = el.source_region
     AND ec.event_id = el.event_id
    WHERE {" AND ".join(where)}
    GROUP BY item_type
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
    return [_coerce_metric_row(row, key_name) for row in rows]


async def _fetch_grouped_build_rows_from_raw(
    conn: psycopg.AsyncConnection,
    *,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    kill_area: str | None,
    build_key: str | None = None,
    slot_filter: tuple[str, str] | None = None,
    slot_filter_any: tuple[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    lower_day = utc_day_lower_bound(days)
    where, params = _raw_filter_sql(
        lower_day=lower_day,
        region=region,
        patch_id=patch_id,
        content_type=content_type,
        fight_scale=fight_scale,
        kill_area=kill_area,
    )
    where.extend(["el.build_key IS NOT NULL", "el.build_key <> ''"])
    if build_key is not None:
        where.append("el.build_key = %s")
        params.append(build_key)
    if slot_filter is not None:
        slot, item_type = slot_filter
        column = SLOT_TO_COLUMN[slot]
        where.append(f"el.{column} = %s")
        params.append(item_type)
    if slot_filter_any is not None:
        slot, item_types = slot_filter_any
        column = SLOT_TO_COLUMN[slot]
        where.append(f"el.{column} = ANY(%s)")
        params.append(item_types)
    sql = f"""
    SELECT
      el.build_key,
      SUM(
        CASE
          WHEN el.perspective = 'victim' THEN 0.0
          ELSE 1.0 / GREATEST(ec.observed_kill_side_count, 1)
        END
      ) AS kill_credit,
      SUM(CASE WHEN el.perspective = 'victim' THEN 1.0 ELSE 0.0 END) AS death_count,
      COUNT(*) AS appearance_count,
      COUNT(DISTINCT (el.source_region, el.event_id)) AS event_count,
      AVG(el.average_item_power) AS avg_item_power,
      SUM(COALESCE(el.kill_fame, el.total_victim_kill_fame, 0)) AS total_kill_fame
    FROM event_loadouts el
    JOIN event_contexts ec
      ON ec.source_region = el.source_region
     AND ec.event_id = el.event_id
    WHERE {" AND ".join(where)}
    GROUP BY el.build_key
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
    return [_coerce_metric_row(row, "build_key") for row in rows]


async def _fetch_item_distribution_from_raw(
    conn: psycopg.AsyncConnection,
    *,
    slot: str,
    item_type: str,
    group_sql: str,
    key_name: str,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    kill_area: str | None,
) -> list[dict[str, Any]]:
    lower_day = utc_day_lower_bound(days)
    column = SLOT_TO_COLUMN[slot]
    where, params = _raw_filter_sql(
        lower_day=lower_day,
        region=region,
        patch_id=patch_id,
        content_type=content_type,
        fight_scale=fight_scale,
        kill_area=kill_area,
    )
    where.append(f"el.{column} = %s")
    params.append(item_type)
    sql = f"""
    SELECT
      {group_sql} AS group_key,
      SUM(
        CASE
          WHEN el.perspective = 'victim' THEN 0.0
          ELSE 1.0 / GREATEST(ec.observed_kill_side_count, 1)
        END
      ) AS kill_credit,
      SUM(CASE WHEN el.perspective = 'victim' THEN 1.0 ELSE 0.0 END) AS death_count,
      COUNT(*) AS appearance_count,
      COUNT(DISTINCT (el.source_region, el.event_id)) AS event_count,
      AVG(el.average_item_power) AS avg_item_power,
      SUM(COALESCE(el.kill_fame, el.total_victim_kill_fame, 0)) AS total_kill_fame
    FROM event_loadouts el
    JOIN event_contexts ec
      ON ec.source_region = el.source_region
     AND ec.event_id = el.event_id
    WHERE {" AND ".join(where)}
    GROUP BY group_key
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
    return [_coerce_metric_row(row, key_name) for row in rows]


async def _fetch_build_distribution_from_raw(
    conn: psycopg.AsyncConnection,
    *,
    build_key: str,
    group_sql: str,
    key_name: str,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    kill_area: str | None,
) -> list[dict[str, Any]]:
    lower_day = utc_day_lower_bound(days)
    where, params = _raw_filter_sql(
        lower_day=lower_day,
        region=region,
        patch_id=patch_id,
        content_type=content_type,
        fight_scale=fight_scale,
        kill_area=kill_area,
    )
    where.append("el.build_key = %s")
    params.append(build_key)
    sql = f"""
    SELECT
      {group_sql} AS group_key,
      SUM(
        CASE
          WHEN el.perspective = 'victim' THEN 0.0
          ELSE 1.0 / GREATEST(ec.observed_kill_side_count, 1)
        END
      ) AS kill_credit,
      SUM(CASE WHEN el.perspective = 'victim' THEN 1.0 ELSE 0.0 END) AS death_count,
      COUNT(*) AS appearance_count,
      COUNT(DISTINCT (el.source_region, el.event_id)) AS event_count,
      AVG(el.average_item_power) AS avg_item_power,
      SUM(COALESCE(el.kill_fame, el.total_victim_kill_fame, 0)) AS total_kill_fame
    FROM event_loadouts el
    JOIN event_contexts ec
      ON ec.source_region = el.source_region
     AND ec.event_id = el.event_id
    WHERE {" AND ".join(where)}
    GROUP BY group_key
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
    return [_coerce_metric_row(row, key_name) for row in rows]


def _sort_leaderboard_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["adjusted_score"],
            row["sample"],
            row["appearance_count"],
        ),
        reverse=True,
    )


def _sort_build_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["appearance_count"],
            row["adjusted_score"],
            row["sample"],
        ),
        reverse=True,
    )


def _build_top_build_map(build_rows: list[dict[str, Any]]) -> dict[str, str]:
    if not build_rows:
        return {}
    baseline_rate = _baseline_rate(build_rows)
    total_appearance_count = sum(row["appearance_count"] for row in build_rows)
    scored_rows = [
        _scored_row(row, baseline_rate=baseline_rate, total_appearance_count=total_appearance_count)
        for row in build_rows
    ]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in scored_rows:
        main_hand_type = build_key_slot_value(row["build_key"], "main_hand")
        if main_hand_type is None:
            continue
        grouped.setdefault(main_hand_type, []).append(row)
    return {
        item_type: _sort_build_rows(candidate_rows)[0]["build_key"]
        for item_type, candidate_rows in grouped.items()
    }


async def fetch_main_hand_leaderboard(
    conn: psycopg.AsyncConnection,
    *,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    kill_area: str | None,
    limit: int,
    min_sample: int,
) -> list[dict[str, Any]]:
    if kill_area is None:
        item_rows = await _fetch_grouped_item_rows_from_aggregates(
            conn,
            slot="main_hand",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
        )
        build_rows = await _fetch_grouped_build_rows_from_aggregates(
            conn,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
        )
    else:
        item_rows = await _fetch_grouped_item_rows_from_raw(
            conn,
            slot="main_hand",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
            kill_area=kill_area,
        )
        build_rows = await _fetch_grouped_build_rows_from_raw(
            conn,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
            kill_area=kill_area,
        )

    if not item_rows:
        return []
    baseline_rate = _baseline_rate(item_rows)
    total_appearance_count = sum(row["appearance_count"] for row in item_rows)
    top_build_by_item = _build_top_build_map(build_rows)
    scored_rows = [
        {
            **_scored_row(
                row,
                baseline_rate=baseline_rate,
                total_appearance_count=total_appearance_count,
            ),
            "top_build_key": top_build_by_item.get(row["item_type"]),
        }
        for row in item_rows
    ]
    filtered = [row for row in scored_rows if row["sample"] >= min_sample]
    return _sort_leaderboard_rows(filtered)[:limit]


async def fetch_slot_family_leaderboard(
    conn: psycopg.AsyncConnection,
    *,
    slot: str,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    kill_area: str | None,
    limit: int,
    min_sample: int,
) -> list[dict[str, Any]]:
    if kill_area is None:
        item_rows = await _fetch_grouped_item_rows_from_aggregates(
            conn,
            slot=slot,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
        )
    else:
        item_rows = await _fetch_grouped_item_rows_from_raw(
            conn,
            slot=slot,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
            kill_area=kill_area,
        )

    if not item_rows:
        return []

    family_rows, _ = _group_item_rows_by_family(item_rows)
    baseline_rate = _baseline_rate(family_rows)
    total_appearance_count = sum(row["appearance_count"] for row in family_rows)
    scored_rows = [
        _scored_row(
            row,
            baseline_rate=baseline_rate,
            total_appearance_count=total_appearance_count,
        )
        for row in family_rows
    ]
    filtered = [row for row in scored_rows if row["sample"] >= min_sample]
    return _sort_leaderboard_rows(filtered)[:limit]


def _by_patch_distribution_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    distributions: list[dict[str, Any]] = []
    for row in rows:
        patch_key = row["patch_key"]
        distributions.append(
            {
                **_distribution_row(row),
                "patch_id": None if patch_key == 0 else int(patch_key),
            }
        )
    return sorted(distributions, key=lambda row: (row["patch_id"] is None, row["patch_id"]))


async def fetch_item_detail(
    conn: psycopg.AsyncConnection,
    *,
    slot: str,
    item_type: str,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    kill_area: str | None,
) -> dict[str, Any] | None:
    if kill_area is None:
        all_item_rows = await _fetch_grouped_item_rows_from_aggregates(
            conn,
            slot=slot,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
        )
        if not all_item_rows:
            return None
        baseline_rate = _baseline_rate(all_item_rows)
        total_appearance_count = sum(row["appearance_count"] for row in all_item_rows)
        item_row = next((row for row in all_item_rows if row["item_type"] == item_type), None)
        if item_row is None:
            return None

        build_rows = await _fetch_grouped_build_rows_from_aggregates(
            conn,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
            main_hand_item_type=item_type,
        )
        by_content_type = await _fetch_grouped_item_rows_from_aggregates(
            conn,
            slot=slot,
            item_type=item_type,
            group_sql="content_type",
            key_name="content_type",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=None,
            fight_scale=fight_scale,
        )
        by_fight_scale = await _fetch_grouped_item_rows_from_aggregates(
            conn,
            slot=slot,
            item_type=item_type,
            group_sql="fight_scale_bucket",
            key_name="fight_scale",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=None,
        )
        by_patch = await _fetch_grouped_item_rows_from_aggregates(
            conn,
            slot=slot,
            item_type=item_type,
            group_sql="patch_id",
            key_name="patch_key",
            days=days,
            region=region,
            patch_id=None,
            content_type=content_type,
            fight_scale=fight_scale,
        )
    else:
        all_item_rows = await _fetch_grouped_item_rows_from_raw(
            conn,
            slot=slot,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
            kill_area=kill_area,
        )
        if not all_item_rows:
            return None
        baseline_rate = _baseline_rate(all_item_rows)
        total_appearance_count = sum(row["appearance_count"] for row in all_item_rows)
        item_row = next((row for row in all_item_rows if row["item_type"] == item_type), None)
        if item_row is None:
            return None

        build_rows = await _fetch_grouped_build_rows_from_raw(
            conn,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
            kill_area=kill_area,
            slot_filter=(slot, item_type),
        )
        by_content_type = await _fetch_item_distribution_from_raw(
            conn,
            slot=slot,
            item_type=item_type,
            group_sql="ec.content_type",
            key_name="content_type",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=None,
            fight_scale=fight_scale,
            kill_area=kill_area,
        )
        by_fight_scale = await _fetch_item_distribution_from_raw(
            conn,
            slot=slot,
            item_type=item_type,
            group_sql="ec.fight_scale_bucket",
            key_name="fight_scale",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=None,
            kill_area=kill_area,
        )
        by_patch = await _fetch_item_distribution_from_raw(
            conn,
            slot=slot,
            item_type=item_type,
            group_sql="COALESCE(el.patch_id, 0)",
            key_name="patch_key",
            days=days,
            region=region,
            patch_id=None,
            content_type=content_type,
            fight_scale=fight_scale,
            kill_area=kill_area,
        )

    build_baseline = _baseline_rate(build_rows) if build_rows else 0.5
    build_total_appearance_count = sum(row["appearance_count"] for row in build_rows)
    scored_build_rows = [
        {
            **_scored_row(
                row,
                baseline_rate=build_baseline,
                total_appearance_count=build_total_appearance_count,
            ),
            "components": parse_build_key(row["build_key"]),
        }
        for row in build_rows
    ]
    top_builds = _sort_build_rows(scored_build_rows)[:5]

    return {
        "slot": slot,
        "item_type": item_type,
        "summary": _scored_row(
            item_row,
            baseline_rate=baseline_rate,
            total_appearance_count=total_appearance_count,
        ),
        "distributions": {
            "by_content_type": [_distribution_row(row) for row in by_content_type],
            "by_fight_scale": [_distribution_row(row) for row in by_fight_scale],
            "by_patch": _by_patch_distribution_rows(by_patch),
        },
        "builds": {
            "representative_build": top_builds[0] if top_builds else None,
            "top_builds": top_builds,
        },
    }


async def fetch_item_family_detail(
    conn: psycopg.AsyncConnection,
    *,
    slot: str,
    family_key: str,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    kill_area: str | None,
) -> dict[str, Any] | None:
    if kill_area is None:
        all_item_rows = await _fetch_grouped_item_rows_from_aggregates(
            conn,
            slot=slot,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
        )
    else:
        all_item_rows = await _fetch_grouped_item_rows_from_raw(
            conn,
            slot=slot,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
            kill_area=kill_area,
        )

    if not all_item_rows:
        return None

    family_rows, representative_item_types = _group_item_rows_by_family(all_item_rows)
    family_row = next((row for row in family_rows if row["family_key"] == family_key), None)
    if family_row is None:
        return None

    family_item_rows = [
        row for row in all_item_rows if item_family_key(row["item_type"]) == family_key
    ]
    family_item_types = [row["item_type"] for row in family_item_rows]
    family_baseline = _baseline_rate(family_rows)
    family_total_appearance_count = sum(row["appearance_count"] for row in family_rows)
    variant_baseline = _baseline_rate(all_item_rows)
    variant_total_appearance_count = sum(row["appearance_count"] for row in all_item_rows)

    if kill_area is None:
        build_rows = await _fetch_grouped_build_rows_from_aggregates(
            conn,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
            slot_filter=(slot, family_item_types),
        )
        by_fight_scale = await _fetch_grouped_item_rows_from_aggregates(
            conn,
            slot=slot,
            item_types=family_item_types,
            group_sql="fight_scale_bucket",
            key_name="fight_scale",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=None,
        )
    else:
        build_rows = await _fetch_grouped_build_rows_from_raw(
            conn,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
            kill_area=kill_area,
            slot_filter_any=(slot, family_item_types),
        )
        by_fight_scale = await _fetch_grouped_item_rows_from_raw(
            conn,
            slot=slot,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=None,
            kill_area=kill_area,
            item_types=family_item_types,
            group_sql="ec.fight_scale_bucket",
            key_name="fight_scale",
        )

    build_baseline = _baseline_rate(build_rows) if build_rows else 0.5
    build_total_appearance_count = sum(row["appearance_count"] for row in build_rows)
    scored_build_rows = [
        {
            **_scored_row(
                row,
                baseline_rate=build_baseline,
                total_appearance_count=build_total_appearance_count,
            ),
            "components": parse_build_key(row["build_key"]),
        }
        for row in build_rows
    ]
    variants = [
        _scored_row(
            row,
            baseline_rate=variant_baseline,
            total_appearance_count=variant_total_appearance_count,
        )
        for row in family_item_rows
    ]

    return {
        "slot": slot,
        "family_key": family_key,
        "representative_item_type": representative_item_types[family_key],
        "summary": _scored_row(
            family_row,
            baseline_rate=family_baseline,
            total_appearance_count=family_total_appearance_count,
        ),
        "variants": _sort_build_rows(variants),
        "distributions": {
            "by_fight_scale": [_distribution_row(row) for row in by_fight_scale],
        },
        "builds": {
            "top_builds": _sort_build_rows(scored_build_rows)[:5],
        },
    }


async def fetch_build_detail(
    conn: psycopg.AsyncConnection,
    *,
    build_key: str,
    days: int,
    region: str | None,
    patch_id: int | None,
    content_type: str | None,
    fight_scale: str | None,
    kill_area: str | None,
) -> dict[str, Any] | None:
    if kill_area is None:
        all_build_rows = await _fetch_grouped_build_rows_from_aggregates(
            conn,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
        )
        if not all_build_rows:
            return None
        baseline_rate = _baseline_rate(all_build_rows)
        total_appearance_count = sum(row["appearance_count"] for row in all_build_rows)
        build_row = next((row for row in all_build_rows if row["build_key"] == build_key), None)
        if build_row is None:
            return None

        by_content_type = await _fetch_grouped_build_rows_from_aggregates(
            conn,
            build_key=build_key,
            group_sql="content_type",
            key_name="content_type",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=None,
            fight_scale=fight_scale,
        )
        by_fight_scale = await _fetch_grouped_build_rows_from_aggregates(
            conn,
            build_key=build_key,
            group_sql="fight_scale_bucket",
            key_name="fight_scale",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=None,
        )
        by_patch = await _fetch_grouped_build_rows_from_aggregates(
            conn,
            build_key=build_key,
            group_sql="patch_id",
            key_name="patch_key",
            days=days,
            region=region,
            patch_id=None,
            content_type=content_type,
            fight_scale=fight_scale,
        )
    else:
        all_build_rows = await _fetch_grouped_build_rows_from_raw(
            conn,
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=fight_scale,
            kill_area=kill_area,
        )
        if not all_build_rows:
            return None
        baseline_rate = _baseline_rate(all_build_rows)
        total_appearance_count = sum(row["appearance_count"] for row in all_build_rows)
        build_row = next((row for row in all_build_rows if row["build_key"] == build_key), None)
        if build_row is None:
            return None

        by_content_type = await _fetch_build_distribution_from_raw(
            conn,
            build_key=build_key,
            group_sql="ec.content_type",
            key_name="content_type",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=None,
            fight_scale=fight_scale,
            kill_area=kill_area,
        )
        by_fight_scale = await _fetch_build_distribution_from_raw(
            conn,
            build_key=build_key,
            group_sql="ec.fight_scale_bucket",
            key_name="fight_scale",
            days=days,
            region=region,
            patch_id=patch_id,
            content_type=content_type,
            fight_scale=None,
            kill_area=kill_area,
        )
        by_patch = await _fetch_build_distribution_from_raw(
            conn,
            build_key=build_key,
            group_sql="COALESCE(el.patch_id, 0)",
            key_name="patch_key",
            days=days,
            region=region,
            patch_id=None,
            content_type=content_type,
            fight_scale=fight_scale,
            kill_area=kill_area,
        )

    return {
        "build_key": build_key,
        "components": parse_build_key(build_key),
        "summary": _scored_row(
            build_row,
            baseline_rate=baseline_rate,
            total_appearance_count=total_appearance_count,
        ),
        "distributions": {
            "by_content_type": [_distribution_row(row) for row in by_content_type],
            "by_fight_scale": [_distribution_row(row) for row in by_fight_scale],
            "by_patch": _by_patch_distribution_rows(by_patch),
        },
    }
