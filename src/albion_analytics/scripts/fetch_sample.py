"""Sample: resolve a player and print kill summary."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from albion_analytics.analysis import summarize_kills
from albion_analytics.api import GameinfoClient
from albion_analytics.ingestion import fetch_player_kill_events


async def _run(name: str, max_events: int) -> int:
    client = GameinfoClient()
    pid, events = await fetch_player_kill_events(client, name, max_events=max_events)
    if not pid:
        print(f"Player not found: {name!r}", file=sys.stderr)
        return 1
    summary = summarize_kills(events)
    out = {
        "player_id": pid,
        "fetched_kills": len(events),
        "summary": summary,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch sample kills for a player name")
    p.add_argument("name", help="Exact in-game player name")
    p.add_argument(
        "-n",
        "--max-events",
        type=int,
        default=20,
        help="Max kill events to parse (default 20)",
    )
    args = p.parse_args()
    raise SystemExit(asyncio.run(_run(args.name, args.max_events)))


if __name__ == "__main__":
    main()
