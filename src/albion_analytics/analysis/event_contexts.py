"""Classify event content and fight scale from normalized kill-event metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

CONTENT_TYPES: tuple[str, ...] = (
    "corrupted_dungeon",
    "mists",
    "hellgate",
    "roads",
    "abyssal",
    "unknown",
)
FIGHT_SCALE_BUCKETS: tuple[str, ...] = (
    "solo",
    "duo",
    "small_party",
    "party",
    "large_party",
    "zvz",
    "unknown",
)
EVENT_CONTEXT_CLASSIFIER_VERSION = 1

ContentType = Literal[
    "corrupted_dungeon",
    "mists",
    "hellgate",
    "roads",
    "abyssal",
    "unknown",
]
FightScaleBucket = Literal[
    "solo",
    "duo",
    "small_party",
    "party",
    "large_party",
    "zvz",
    "unknown",
]

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class EventContext:
    source_region: str
    event_id: int
    time_stamp: datetime
    kill_area_raw: str | None
    kill_area_slug: str | None
    content_type: ContentType
    fight_scale_bucket: FightScaleBucket
    reported_participant_count: int | None
    observed_kill_side_count: int
    classifier_version: int = EVENT_CONTEXT_CLASSIFIER_VERSION


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_kill_area_slug(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _NON_ALNUM_RE.sub("_", value.strip().lower()).strip("_")
    return normalized or None


def classify_content_type(kill_area_slug: str | None) -> ContentType:
    if not kill_area_slug:
        return "unknown"
    if kill_area_slug.startswith("corrupted"):
        return "corrupted_dungeon"
    if kill_area_slug.startswith("mist"):
        return "mists"
    if kill_area_slug.startswith("hellgate"):
        return "hellgate"
    if kill_area_slug.startswith("road") or kill_area_slug.startswith("avalon"):
        return "roads"
    if kill_area_slug.startswith("abyss") or kill_area_slug.startswith("depth"):
        return "abyssal"
    return "unknown"


def bucket_fight_scale(reported_participant_count: int | None) -> FightScaleBucket:
    if reported_participant_count is None or reported_participant_count <= 0:
        return "unknown"
    if reported_participant_count == 1:
        return "solo"
    if reported_participant_count == 2:
        return "duo"
    if reported_participant_count <= 5:
        return "small_party"
    if reported_participant_count <= 10:
        return "party"
    if reported_participant_count <= 20:
        return "large_party"
    return "zvz"


def build_event_context(
    *,
    source_region: str,
    event_id: int,
    time_stamp: datetime,
    raw_event: dict[str, Any],
) -> EventContext:
    participants = raw_event.get("Participants")
    participant_count = len(participants) if isinstance(participants, list) else 0
    observed_kill_side_count = max(1, 1 + participant_count)
    reported_participant_count = _as_int(raw_event.get("NumberOfParticipants"))
    if reported_participant_count is None:
        reported_participant_count = observed_kill_side_count

    kill_area_raw = raw_event.get("KillArea")
    kill_area = str(kill_area_raw) if kill_area_raw is not None else None
    kill_area_slug = normalize_kill_area_slug(kill_area)

    return EventContext(
        source_region=source_region,
        event_id=event_id,
        time_stamp=time_stamp,
        kill_area_raw=kill_area,
        kill_area_slug=kill_area_slug,
        content_type=classify_content_type(kill_area_slug),
        fight_scale_bucket=bucket_fight_scale(reported_participant_count),
        reported_participant_count=reported_participant_count,
        observed_kill_side_count=observed_kill_side_count,
    )
