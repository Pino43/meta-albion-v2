"""Print item rankings from daily_item_usage."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from albion_analytics.config import get_settings
from albion_analytics.storage.aggregates_repo import SLOT_TO_COLUMN, fetch_item_rankings
from albion_analytics.storage.db import connect_database


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


async def _run(
    *,
    slot: str,
    perspective: str,
    region: str | None,
    days: int,
    limit: int,
) -> int:
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    conn = await connect_database(s)
    try:
        rows = await fetch_item_rankings(
            conn,
            slot=slot,
            perspective=perspective,
            days=days,
            region=region,
            limit=limit,
        )
    finally:
        await conn.close()

    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Show ranked item usage from daily aggregates")
    p.add_argument("--slot", required=True, choices=sorted(SLOT_TO_COLUMN))
    p.add_argument(
        "--perspective",
        default="killer",
        choices=["killer", "victim", "participant"],
        help="Loadout perspective to query (default: killer)",
    )
    p.add_argument("--region", choices=["europe", "americas", "asia"], default=None)
    p.add_argument("--days", type=positive_int, default=7)
    p.add_argument("--limit", type=positive_int, default=20)
    args = p.parse_args()
    raise SystemExit(
        asyncio.run(
            _run(
                slot=args.slot,
                perspective=args.perspective,
                region=args.region,
                days=args.days,
                limit=args.limit,
            )
        )
    )


if __name__ == "__main__":
    main()
