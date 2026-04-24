"""Read-only operational status queries."""

from __future__ import annotations

from typing import Any

import psycopg

CORE_STATUS_TABLES: tuple[str, ...] = (
    "kill_events",
    "event_loadouts",
    "event_contexts",
    "battle_contexts",
    "daily_item_usage",
    "daily_build_usage",
    "daily_item_outcomes",
    "daily_build_outcomes",
)


async def check_core_tables(conn: psycopg.AsyncConnection) -> list[str]:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN (
                'kill_events',
                'event_loadouts',
                'event_contexts',
                'battle_contexts',
                'daily_item_usage',
                'daily_build_usage',
                'daily_item_outcomes',
                'daily_build_outcomes'
              )
            """
        )
        rows = await cur.fetchall()

    present = {row[0] for row in rows}
    return [table for table in CORE_STATUS_TABLES if table not in present]


async def fetch_api_status(conn: psycopg.AsyncConnection) -> dict[str, Any]:
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT 'kill_events' AS table_name, count(*) FROM kill_events
            UNION ALL
            SELECT 'event_loadouts', count(*) FROM event_loadouts
            UNION ALL
            SELECT 'event_contexts', count(*) FROM event_contexts
            UNION ALL
            SELECT 'battle_contexts', count(*) FROM battle_contexts
            UNION ALL
            SELECT 'daily_item_usage', count(*) FROM daily_item_usage
            UNION ALL
            SELECT 'daily_build_usage', count(*) FROM daily_build_usage
            UNION ALL
            SELECT 'daily_item_outcomes', count(*) FROM daily_item_outcomes
            UNION ALL
            SELECT 'daily_build_outcomes', count(*) FROM daily_build_outcomes
            """
        )
        count_rows = await cur.fetchall()

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
              patch_rows_updated,
              normalized_loadouts,
              classified_contexts,
              aggregated_item_rows,
              aggregated_build_rows,
              aggregated_outcome_item_rows,
              aggregated_outcome_build_rows,
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
            "patch_rows_updated": run[7],
            "normalized_loadouts": run[8],
            "classified_contexts": run[9],
            "aggregated_item_rows": run[10],
            "aggregated_build_rows": run[11],
            "aggregated_outcome_item_rows": run[12],
            "aggregated_outcome_build_rows": run[13],
            "error_message": run[14],
        }

    return {
        "tables": {row[0]: row[1] for row in count_rows},
        "latest_collector_run": latest_run,
    }
