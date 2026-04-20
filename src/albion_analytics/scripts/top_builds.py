"""Print top build fingerprints from normalized event_loadouts."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from albion_analytics.config import get_settings
from albion_analytics.storage.db import connect_database


async def _run(
    *,
    perspective: str,
    region: str | None,
    days: int | None,
    limit: int,
) -> int:
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    where = ["build_key IS NOT NULL", "build_key <> ''", "perspective = %s"]
    params: list[Any] = [perspective]
    if region:
        where.append("source_region = %s")
        params.append(region)
    if days is not None:
        where.append("time_stamp >= NOW() - (%s::int * INTERVAL '1 day')")
        params.append(days)
    params.append(limit)

    sql = f"""
    SELECT
      build_key,
      count(*) AS uses,
      count(DISTINCT (source_region, event_id)) AS events,
      avg(average_item_power) AS avg_item_power
    FROM event_loadouts
    WHERE {" AND ".join(where)}
    GROUP BY build_key
    ORDER BY uses DESC
    LIMIT %s
    """

    conn = await connect_database(s)
    try:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
    finally:
        await conn.close()

    print(
        json.dumps(
            [
                {
                    "build_key": row[0],
                    "uses": row[1],
                    "events": row[2],
                    "avg_item_power": float(row[3]) if row[3] is not None else None,
                }
                for row in rows
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Show top build fingerprints from event_loadouts")
    p.add_argument(
        "--perspective",
        default="killer",
        choices=["killer", "victim", "participant"],
        help="Loadout perspective to query (default: killer)",
    )
    p.add_argument("--region", choices=["europe", "americas", "asia"], default=None)
    p.add_argument("--days", type=int, default=None, help="Limit to recent N days")
    p.add_argument("--limit", type=int, default=20)
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
