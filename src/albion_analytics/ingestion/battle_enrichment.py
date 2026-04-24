"""Enrich event fight scale from Gameinfo battle summaries."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import psycopg

from albion_analytics.api import GameinfoClient
from albion_analytics.config import Settings, get_settings
from albion_analytics.regions import GAMEINFO_REGIONS
from albion_analytics.storage.battle_contexts_repo import (
    BattleContext,
    apply_battle_contexts_to_event_contexts,
    fetch_pending_battle_refs,
    parse_battle_context,
    upsert_battle_contexts,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BattleEnrichmentResult:
    candidates: int
    requested: int
    fetched: int
    upserted: int
    updated_event_contexts: int
    skipped_invalid: int
    failed: int


async def enrich_battle_contexts(
    conn: psycopg.AsyncConnection,
    *,
    settings: Settings | None = None,
    batch_size: int | None = None,
    max_requests: int | None = None,
) -> BattleEnrichmentResult:
    s = settings or get_settings()
    candidate_limit = batch_size if batch_size is not None else s.battle_enrichment_batch_size
    request_limit = (
        max_requests
        if max_requests is not None
        else s.battle_enrichment_max_requests_per_round
    )
    if candidate_limit <= 0 or request_limit <= 0:
        return BattleEnrichmentResult(0, 0, 0, 0, 0, 0, 0)

    candidates = await fetch_pending_battle_refs(conn, limit=candidate_limit)
    selected = candidates[:request_limit]
    rows: list[BattleContext] = []
    skipped_invalid = 0
    failed = 0

    refs_by_region: dict[str, list[int]] = {}
    for ref in selected:
        refs_by_region.setdefault(ref.source_region, []).append(ref.battle_id)

    for region, battle_ids in refs_by_region.items():
        base_url = GAMEINFO_REGIONS.get(region)
        if base_url is None:
            failed += len(battle_ids)
            logger.warning(
                "battle_enrichment skipped unknown region=%s count=%s",
                region,
                len(battle_ids),
            )
            continue

        async with GameinfoClient(base_url=base_url) as client:
            for battle_id in battle_ids:
                try:
                    payload = await client.get_battle(battle_id)
                except Exception:
                    failed += 1
                    logger.exception(
                        "battle_enrichment fetch_failed region=%s battle_id=%s",
                        region,
                        battle_id,
                    )
                    continue

                context = parse_battle_context(source_region=region, payload=payload)
                if context is None:
                    skipped_invalid += 1
                    continue
                rows.append(context)

    upserted = await upsert_battle_contexts(conn, rows)
    updated_contexts = await apply_battle_contexts_to_event_contexts(conn) if rows else 0
    result = BattleEnrichmentResult(
        candidates=len(candidates),
        requested=len(selected),
        fetched=len(rows),
        upserted=upserted,
        updated_event_contexts=updated_contexts,
        skipped_invalid=skipped_invalid,
        failed=failed,
    )
    logger.info(
        (
            "battle_enrichment candidates=%s requested=%s fetched=%s upserted=%s "
            "updated_event_contexts=%s skipped_invalid=%s failed=%s"
        ),
        result.candidates,
        result.requested,
        result.fetched,
        result.upserted,
        result.updated_event_contexts,
        result.skipped_invalid,
        result.failed,
    )
    return result
