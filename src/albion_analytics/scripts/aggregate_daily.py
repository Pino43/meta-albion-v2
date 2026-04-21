"""Refresh daily aggregate tables from event_loadouts."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from albion_analytics.config import get_settings
from albion_analytics.storage.aggregates_repo import aggregate_daily_usage
from albion_analytics.storage.db import connect_database
from albion_analytics.storage.outcomes_repo import aggregate_daily_outcomes
from albion_analytics.storage.schema import apply_schema

logger = logging.getLogger(__name__)


async def _run(*, lookback_days: int) -> int:
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    conn = await connect_database(s)
    try:
        await apply_schema(conn)
        usage_result = await aggregate_daily_usage(conn, lookback_days=lookback_days)
        outcome_result = await aggregate_daily_outcomes(conn, lookback_days=lookback_days)
    finally:
        await conn.close()

    print(
        json.dumps(
            {
                "lookback_days": lookback_days,
                "aggregated_item_rows": usage_result.item_rows,
                "aggregated_build_rows": usage_result.build_rows,
                "aggregated_outcome_item_rows": outcome_result.item_rows,
                "aggregated_outcome_build_rows": outcome_result.build_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(
        description="Refresh daily item/build usage aggregates and outcome aggregates"
    )
    p.add_argument(
        "--lookback-days",
        type=int,
        default=3,
        help="Recent UTC days to refresh, including today (default: 3)",
    )
    args = p.parse_args()
    raise SystemExit(asyncio.run(_run(lookback_days=args.lookback_days)))


if __name__ == "__main__":
    main()
