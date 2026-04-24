"""Backfill compact battle summaries and fight-scale buckets."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from albion_analytics.config import get_settings
from albion_analytics.ingestion.battle_enrichment import enrich_battle_contexts
from albion_analytics.storage.db import connect_database
from albion_analytics.storage.schema import apply_schema


async def _run(*, batch_size: int, max_requests: int) -> int:
    settings = get_settings()
    if not settings.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    conn = await connect_database(settings)
    try:
        await apply_schema(conn)
        result = await enrich_battle_contexts(
            conn,
            settings=settings,
            batch_size=batch_size,
            max_requests=max_requests,
        )
    finally:
        await conn.close()

    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Fetch Gameinfo battle summaries and enrich event fight scale"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=get_settings().battle_enrichment_batch_size,
        help="Pending battle ids to inspect (default: BATTLE_ENRICHMENT_BATCH_SIZE)",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=get_settings().battle_enrichment_max_requests_per_round,
        help=(
            "Maximum Gameinfo battle requests to make "
            "(default: BATTLE_ENRICHMENT_MAX_REQUESTS_PER_ROUND)"
        ),
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(batch_size=args.batch_size, max_requests=args.max_requests)))


if __name__ == "__main__":
    main()
