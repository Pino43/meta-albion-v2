"""Apply retention cleanup to bound Postgres storage usage."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from albion_analytics.config import get_settings
from albion_analytics.storage.db import connect_database
from albion_analytics.storage.retention_repo import cleanup_retention
from albion_analytics.storage.schema import apply_schema


async def _run(
    *,
    raw_events_days: int | None,
    daily_aggregate_days: int | None,
    collector_run_days: int | None,
) -> int:
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    conn = await connect_database(s)
    try:
        await apply_schema(conn)
        result = await cleanup_retention(
            conn,
            raw_events_retention_days=raw_events_days or s.raw_events_retention_days,
            daily_aggregate_retention_days=(
                daily_aggregate_days or s.daily_aggregate_retention_days
            ),
            collector_run_retention_days=collector_run_days or s.collector_run_retention_days,
        )
    finally:
        await conn.close()

    print(
        json.dumps(
            {
                "raw_event_cutoff": result.raw_event_cutoff.isoformat(),
                "daily_aggregate_cutoff_day": result.daily_aggregate_cutoff_day.isoformat(),
                "collector_run_cutoff": result.collector_run_cutoff.isoformat(),
                "deleted_kill_events": result.deleted_kill_events,
                "deleted_daily_item_rows": result.deleted_daily_item_rows,
                "deleted_daily_build_rows": result.deleted_daily_build_rows,
                "deleted_collector_runs": result.deleted_collector_runs,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Delete data older than configured retention windows")
    p.add_argument("--raw-events-days", type=positive_int, default=None)
    p.add_argument("--daily-aggregate-days", type=positive_int, default=None)
    p.add_argument("--collector-run-days", type=positive_int, default=None)
    args = p.parse_args()
    raise SystemExit(
        asyncio.run(
            _run(
                raw_events_days=args.raw_events_days,
                daily_aggregate_days=args.daily_aggregate_days,
                collector_run_days=args.collector_run_days,
            )
        )
    )


if __name__ == "__main__":
    main()
