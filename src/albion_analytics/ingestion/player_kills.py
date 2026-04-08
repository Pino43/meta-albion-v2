"""Fetch kill events for a player by in-game name."""

from __future__ import annotations

from albion_analytics.api import GameinfoClient
from albion_analytics.models import KillEvent


async def resolve_player_id(client: GameinfoClient, name: str) -> str | None:
    rows = await client.search_players(name)
    for row in rows:
        pid = row.get("Id") or row.get("id")
        if pid:
            return str(pid)
    return None


async def fetch_player_kill_events(
    client: GameinfoClient,
    player_name: str,
    *,
    max_events: int = 20,
) -> tuple[str | None, list[KillEvent]]:
    """
    Resolve player id, then fetch kills (single page for now).

    Pagination can be added with offset until len < limit.
    """
    pid = await resolve_player_id(client, player_name)
    if not pid:
        return None, []

    raw = await client.get_player_kills(pid, limit=min(51, max_events + 1), offset=0)
    events: list[KillEvent] = []
    for item in raw[:max_events]:
        try:
            events.append(KillEvent.model_validate(item))
        except Exception:
            # Keep pipeline resilient; log/record bad rows in production
            continue
    return pid, events
