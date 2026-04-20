"""Apply Postgres DDL (idempotent)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from albion_analytics.config import get_settings
from albion_analytics.storage.db import connect_database
from albion_analytics.storage.schema import apply_schema

logger = logging.getLogger(__name__)


async def _run() -> int:
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    logger.info("Connecting to Postgres for schema initialization")
    conn = await connect_database(s)
    try:
        await apply_schema(conn)
    finally:
        await conn.close()
    logger.info("Schema initialization complete")
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Create tables for Albion analytics (Postgres)")
    p.parse_args()
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
