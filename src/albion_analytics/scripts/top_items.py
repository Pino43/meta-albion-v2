"""Print top item usage from normalized event_loadouts."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from albion_analytics.config import get_settings
from albion_analytics.storage.db import connect_database

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


async def _run(
    *,
    slot: str,
    perspective: str,
    region: str | None,
    days: int | None,
    limit: int,
) -> int:
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    column = SLOT_TO_COLUMN[slot]
    where = [f"{column} IS NOT NULL", f"{column} <> ''", "perspective = %s"]
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
      {column} AS item_type,
      count(*) AS uses,
      count(DISTINCT (source_region, event_id)) AS events,
      avg(average_item_power) AS avg_item_power
    FROM event_loadouts
    WHERE {" AND ".join(where)}
    GROUP BY {column}
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
                    "item_type": row[0],
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
    p = argparse.ArgumentParser(description="Show top item usage from event_loadouts")
    p.add_argument("--slot", required=True, choices=sorted(SLOT_TO_COLUMN))
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
