"""Backfill event_loadouts from kill_events.raw_json."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from albion_analytics.config import get_settings
from albion_analytics.storage.db import connect_database
from albion_analytics.storage.loadouts_repo import (
    count_pending_event_loadouts,
    normalize_pending_event_loadouts,
)
from albion_analytics.storage.schema import apply_schema

logger = logging.getLogger(__name__)


async def _run(*, batch_size: int, max_batches: int) -> int:
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    conn = await connect_database(s)
    total_normalized = 0
    batches = 0
    try:
        await apply_schema(conn)
        while batches < max_batches:
            pending_before = await count_pending_event_loadouts(conn)
            if pending_before <= 0:
                break
            normalized = await normalize_pending_event_loadouts(conn, limit=batch_size)
            total_normalized += normalized
            batches += 1
            if normalized <= 0 and pending_before <= batch_size:
                break

        pending_after = await count_pending_event_loadouts(conn)
    finally:
        await conn.close()

    print(
        json.dumps(
            {
                "batches": batches,
                "normalized_loadouts": total_normalized,
                "pending_events": pending_after,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Normalize raw kill events into event_loadouts")
    p.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Kill events to scan per batch (default: 1000)",
    )
    p.add_argument(
        "--max-batches",
        type=int,
        default=100,
        help="Maximum batches to run before exiting (default: 100)",
    )
    args = p.parse_args()
    raise SystemExit(asyncio.run(_run(batch_size=args.batch_size, max_batches=args.max_batches)))


if __name__ == "__main__":
    main()
