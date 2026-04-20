"""Continuously poll Gameinfo /events and store in Postgres (deduped)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
import time

import psycopg

from albion_analytics.config import get_settings
from albion_analytics.ingestion.event_feed import collect_events_round
from albion_analytics.storage.aggregates_repo import aggregate_daily_usage
from albion_analytics.storage.db import connect_database
from albion_analytics.storage.events_repo import finish_collector_run, start_collector_run
from albion_analytics.storage.loadouts_repo import normalize_pending_event_loadouts
from albion_analytics.storage.schema import apply_schema

logger = logging.getLogger(__name__)


def _install_signal_handlers(shutdown_event: asyncio.Event) -> None:
    def request_shutdown(signum: int, _frame: object) -> None:
        logger.info("Received signal %s; stopping after the current round", signum)
        shutdown_event.set()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            signal.signal(sig, request_shutdown)


async def _sleep_until_shutdown(shutdown_event: asyncio.Event, seconds: float) -> None:
    if seconds <= 0:
        return
    try:
        await asyncio.wait_for(shutdown_event.wait(), timeout=seconds)
    except TimeoutError:
        pass


async def _run(*, once: bool, interval: float | None, limit: int | None) -> int:
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    poll = interval if interval is not None else s.collect_poll_interval_sec
    shutdown_event = asyncio.Event()
    _install_signal_handlers(shutdown_event)

    conn: psycopg.AsyncConnection | None = None
    exit_code = 0
    schema_ready = False

    try:
        while not shutdown_event.is_set():
            run_id: int | None = None
            started_at = time.monotonic()

            try:
                if conn is None or conn.closed:
                    conn = await connect_database(s)
                    schema_ready = False

                if not schema_ready:
                    logger.info("Applying database schema before collection")
                    await apply_schema(conn)
                    schema_ready = True

                run_id = await start_collector_run(conn)
                results, patch_n = await collect_events_round(
                    conn,
                    limit=limit,
                )
                normalized_loadouts = 0
                if s.collect_normalize_after_round:
                    normalized_loadouts = await normalize_pending_event_loadouts(
                        conn,
                        limit=s.normalize_batch_size,
                    )
                aggregated_item_rows = 0
                aggregated_build_rows = 0
                if s.collect_aggregate_after_round:
                    aggregate_result = await aggregate_daily_usage(
                        conn,
                        lookback_days=s.aggregate_lookback_days,
                    )
                    aggregated_item_rows = aggregate_result.item_rows
                    aggregated_build_rows = aggregate_result.build_rows
                totals = {
                    "total_fetched": sum(r.fetched for r in results),
                    "total_inserted": sum(r.inserted for r in results),
                    "total_skipped_invalid": sum(r.skipped_invalid for r in results),
                }
                await finish_collector_run(
                    conn,
                    run_id,
                    status="success",
                    patch_rows_updated=patch_n,
                    normalized_loadouts=normalized_loadouts,
                    aggregated_item_rows=aggregated_item_rows,
                    aggregated_build_rows=aggregated_build_rows,
                    **totals,
                )
                logger.info(
                    (
                        "collection_round status=success fetched=%s inserted=%s "
                        "skipped_invalid=%s patch_updated=%s normalized_loadouts=%s "
                        "aggregated_item_rows=%s aggregated_build_rows=%s "
                        "duration_sec=%.3f"
                    ),
                    totals["total_fetched"],
                    totals["total_inserted"],
                    totals["total_skipped_invalid"],
                    patch_n,
                    normalized_loadouts,
                    aggregated_item_rows,
                    aggregated_build_rows,
                    time.monotonic() - started_at,
                )
            except Exception as exc:
                duration_sec = time.monotonic() - started_at
                logger.exception(
                    "collection_round status=failed duration_sec=%.3f error=%s",
                    duration_sec,
                    exc,
                )

                if conn is not None and not conn.closed:
                    try:
                        await conn.rollback()
                    except Exception:
                        logger.exception("Failed to rollback after collection error")

                    if run_id is not None:
                        try:
                            await finish_collector_run(
                                conn,
                                run_id,
                                status="failed",
                                error_message=str(exc),
                            )
                        except Exception:
                            logger.exception("Failed to write failed collector_runs row")
                else:
                    conn = None

                if once:
                    exit_code = 1
                    break

                await _sleep_until_shutdown(shutdown_event, s.collect_error_backoff_sec)
                continue

            if once:
                break
            await _sleep_until_shutdown(shutdown_event, poll)
    finally:
        if conn is not None and not conn.closed:
            await conn.close()

    return exit_code


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Poll Albion Gameinfo /events into Postgres")
    p.add_argument(
        "--once",
        action="store_true",
        help="Single poll cycle then exit (default: loop forever)",
    )
    p.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Seconds between polls (default: COLLECT_POLL_INTERVAL_SEC)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="events per region per request (default: COLLECT_EVENTS_LIMIT)",
    )
    args = p.parse_args()
    raise SystemExit(
        asyncio.run(
            _run(
                once=args.once,
                interval=args.interval,
                limit=args.limit,
            )
        )
    )


if __name__ == "__main__":
    main()
