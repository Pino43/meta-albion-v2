"""Retention cleanup for bounded Postgres storage usage."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import psycopg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetentionCleanupResult:
    raw_event_cutoff: datetime
    daily_aggregate_cutoff_day: date
    collector_run_cutoff: datetime
    deleted_kill_events: int
    deleted_daily_item_rows: int
    deleted_daily_build_rows: int
    deleted_daily_item_outcome_rows: int
    deleted_daily_build_outcome_rows: int
    deleted_collector_runs: int


def retention_datetime_cutoff(
    days: int,
    *,
    now: datetime | None = None,
) -> datetime:
    if days < 1:
        raise ValueError("retention days must be >= 1")
    ref = now or datetime.now(UTC)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    return ref.astimezone(UTC) - timedelta(days=days)


def retention_day_cutoff(
    days: int,
    *,
    now: datetime | None = None,
) -> date:
    if days < 1:
        raise ValueError("retention days must be >= 1")
    ref = now or datetime.now(UTC)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    return ref.astimezone(UTC).date() - timedelta(days=days - 1)


async def cleanup_retention(
    conn: psycopg.AsyncConnection,
    *,
    raw_events_retention_days: int,
    daily_aggregate_retention_days: int,
    collector_run_retention_days: int,
    now: datetime | None = None,
) -> RetentionCleanupResult:
    raw_event_cutoff = retention_datetime_cutoff(raw_events_retention_days, now=now)
    daily_cutoff_day = retention_day_cutoff(daily_aggregate_retention_days, now=now)
    collector_run_cutoff = retention_datetime_cutoff(collector_run_retention_days, now=now)

    async with conn.transaction():
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM kill_events WHERE time_stamp < %s",
                (raw_event_cutoff,),
            )
            deleted_kill_events = cur.rowcount or 0

            await cur.execute(
                "DELETE FROM daily_item_usage WHERE day < %s",
                (daily_cutoff_day,),
            )
            deleted_daily_item_rows = cur.rowcount or 0

            await cur.execute(
                "DELETE FROM daily_build_usage WHERE day < %s",
                (daily_cutoff_day,),
            )
            deleted_daily_build_rows = cur.rowcount or 0

            await cur.execute(
                "DELETE FROM daily_item_outcomes WHERE day < %s",
                (daily_cutoff_day,),
            )
            deleted_daily_item_outcome_rows = cur.rowcount or 0

            await cur.execute(
                "DELETE FROM daily_build_outcomes WHERE day < %s",
                (daily_cutoff_day,),
            )
            deleted_daily_build_outcome_rows = cur.rowcount or 0

            await cur.execute(
                "DELETE FROM collector_runs WHERE started_at < %s",
                (collector_run_cutoff,),
            )
            deleted_collector_runs = cur.rowcount or 0

    logger.info(
        (
            "retention_cleanup deleted_kill_events=%s "
            "deleted_daily_item_rows=%s deleted_daily_build_rows=%s "
            "deleted_daily_item_outcome_rows=%s deleted_daily_build_outcome_rows=%s "
            "deleted_collector_runs=%s raw_event_cutoff=%s "
            "daily_aggregate_cutoff_day=%s collector_run_cutoff=%s"
        ),
        deleted_kill_events,
        deleted_daily_item_rows,
        deleted_daily_build_rows,
        deleted_daily_item_outcome_rows,
        deleted_daily_build_outcome_rows,
        deleted_collector_runs,
        raw_event_cutoff.isoformat(),
        daily_cutoff_day.isoformat(),
        collector_run_cutoff.isoformat(),
    )
    return RetentionCleanupResult(
        raw_event_cutoff=raw_event_cutoff,
        daily_aggregate_cutoff_day=daily_cutoff_day,
        collector_run_cutoff=collector_run_cutoff,
        deleted_kill_events=deleted_kill_events,
        deleted_daily_item_rows=deleted_daily_item_rows,
        deleted_daily_build_rows=deleted_daily_build_rows,
        deleted_daily_item_outcome_rows=deleted_daily_item_outcome_rows,
        deleted_daily_build_outcome_rows=deleted_daily_build_outcome_rows,
        deleted_collector_runs=deleted_collector_runs,
    )
