"""Poll global /events feed per Gameinfo region and store in Postgres."""

from __future__ import annotations

import logging
import time
from typing import Any

import psycopg

from albion_analytics.api import GameinfoClient
from albion_analytics.config import Settings, get_settings
from albion_analytics.regions import GAMEINFO_REGIONS, parse_region_filter
from albion_analytics.storage.events_repo import (
    EventIngestionResult,
    assign_patches_from_ranges,
    get_last_event_id,
    upsert_raw_events,
)

logger = logging.getLogger(__name__)


def _event_id_as_int(event: dict[str, Any]) -> int | None:
    try:
        return int(event["EventId"])
    except (KeyError, TypeError, ValueError):
        return None


async def _fetch_new_events(
    client: GameinfoClient,
    *,
    page_size: int,
    max_pages: int,
    cursor_event_id: int | None,
) -> list[dict[str, Any]]:
    """Paginate /events until already-seen events or configured page limit."""
    all_events: list[dict[str, Any]] = []

    for page in range(max_pages):
        raw = await client.get_recent_events(limit=page_size, offset=page * page_size)
        if not raw:
            break

        if cursor_event_id is None:
            all_events.extend(raw)
        else:
            hit_cursor = False
            for event in raw:
                eid = _event_id_as_int(event)
                if eid is not None and eid <= cursor_event_id:
                    hit_cursor = True
                    break
                all_events.append(event)
            if hit_cursor:
                break

        if len(raw) < page_size:
            break

    return all_events


async def collect_events_round(
    conn: psycopg.AsyncConnection,
    *,
    settings: Settings | None = None,
    limit: int | None = None,
) -> tuple[list[EventIngestionResult], int]:
    """
    Fetch recent events from each configured region, upsert, then assign patch_id rows.

    Returns (per-region results, patch-assigned row count).
    """
    s = settings or get_settings()
    if not s.database_url:
        raise ValueError("database_url (DATABASE_URL) is required for collection")

    regions = parse_region_filter(s.collect_regions)
    page_size = limit if limit is not None else s.collect_events_limit
    results: list[EventIngestionResult] = []

    for region_id in regions:
        started_at = time.monotonic()
        base_url = GAMEINFO_REGIONS[region_id]
        cursor_eid = await get_last_event_id(conn, region_id)
        async with GameinfoClient(base_url=base_url) as client:
            raw = await _fetch_new_events(
                client,
                page_size=page_size,
                max_pages=s.collect_max_pages,
                cursor_event_id=cursor_eid,
            )
        res = await upsert_raw_events(conn, region_id, raw)
        results.append(res)
        logger.info(
            (
                "collection_region region=%s cursor=%s fetched=%s inserted=%s "
                "skipped_invalid=%s duration_sec=%.3f"
            ),
            res.region,
            cursor_eid,
            res.fetched,
            res.inserted,
            res.skipped_invalid,
            time.monotonic() - started_at,
        )

    patch_updated = await assign_patches_from_ranges(conn)
    logger.info("collection_patches patch_updated=%s", patch_updated)
    return results, patch_updated
