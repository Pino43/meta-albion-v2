"""Lightweight aggregates for prototyping."""

from __future__ import annotations

from collections import Counter

from albion_analytics.analysis.build_key import build_fingerprint_from_victim
from albion_analytics.models import KillEvent


def summarize_kills(events: list[KillEvent]) -> dict[str, object]:
    builds = Counter()
    for ev in events:
        fp = build_fingerprint_from_victim(ev.victim)
        if fp is not None:
            builds[fp] += 1
    return {
        "event_count": len(events),
        "distinct_victim_builds": len(builds),
        "top_victim_builds": builds.most_common(10),
    }
