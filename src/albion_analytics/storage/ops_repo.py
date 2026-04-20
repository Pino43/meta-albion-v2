"""Operational health and storage usage queries."""

from __future__ import annotations

from typing import Any

import psycopg


async def fetch_ops_snapshot(conn: psycopg.AsyncConnection) -> dict[str, Any]:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT
              pg_database_size(current_database()) AS database_bytes,
              current_database() AS database_name
            """
        )
        database_row = await cur.fetchone()

        await cur.execute(
            """
            SELECT
              relname AS table_name,
              pg_total_relation_size(oid) AS total_bytes,
              pg_relation_size(oid) AS table_bytes,
              pg_indexes_size(oid) AS index_bytes
            FROM pg_class
            WHERE relkind = 'r'
              AND relnamespace = 'public'::regnamespace
            ORDER BY pg_total_relation_size(oid) DESC
            """
        )
        table_rows = await cur.fetchall()

        await cur.execute(
            """
            SELECT
              id,
              started_at,
              finished_at,
              status,
              total_fetched,
              total_inserted,
              total_skipped_invalid,
              normalized_loadouts,
              aggregated_item_rows,
              aggregated_build_rows,
              error_message
            FROM collector_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        )
        run = await cur.fetchone()

    latest_run: dict[str, Any] | None = None
    if run is not None:
        latest_run = {
            "id": run[0],
            "started_at": run[1],
            "finished_at": run[2],
            "status": run[3],
            "total_fetched": run[4],
            "total_inserted": run[5],
            "total_skipped_invalid": run[6],
            "normalized_loadouts": run[7],
            "aggregated_item_rows": run[8],
            "aggregated_build_rows": run[9],
            "error_message": run[10],
        }

    return {
        "database": {
            "name": database_row[1] if database_row else None,
            "bytes": int(database_row[0]) if database_row else 0,
        },
        "tables": [
            {
                "name": row[0],
                "total_bytes": int(row[1]),
                "table_bytes": int(row[2]),
                "index_bytes": int(row[3]),
            }
            for row in table_rows
        ],
        "latest_collector_run": latest_run,
    }
