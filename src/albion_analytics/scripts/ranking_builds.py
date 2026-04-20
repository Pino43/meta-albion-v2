"""Print build rankings from daily_build_usage."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from albion_analytics.config import get_settings
from albion_analytics.scripts.ranking_items import positive_int
from albion_analytics.storage.aggregates_repo import fetch_build_rankings
from albion_analytics.storage.db import connect_database


async def _run(
    *,
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
        rows = await fetch_build_rankings(
            conn,
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
    p = argparse.ArgumentParser(description="Show ranked build usage from daily aggregates")
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
                perspective=args.perspective,
                region=args.region,
                days=args.days,
                limit=args.limit,
            )
        )
    )


if __name__ == "__main__":
    main()
