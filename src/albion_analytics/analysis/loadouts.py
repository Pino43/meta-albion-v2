"""Extract actor loadouts from raw Gameinfo kill events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

LOADOUT_EXTRACTOR_VERSION = 3

Perspective = Literal["killer", "victim", "participant"]

SLOT_COLUMNS: dict[str, str] = {
    "main_hand_type": "MainHand",
    "off_hand_type": "OffHand",
    "head_type": "Head",
    "armor_type": "Armor",
    "shoes_type": "Shoes",
    "bag_type": "Bag",
    "cape_type": "Cape",
    "mount_type": "Mount",
    "potion_type": "Potion",
    "food_type": "Food",
}

CORE_BUILD_COLUMNS: tuple[str, ...] = (
    "head_type",
    "armor_type",
    "shoes_type",
    "main_hand_type",
    "off_hand_type",
    "cape_type",
)


@dataclass(frozen=True)
class EventLoadout:
    source_region: str
    event_id: int
    perspective: Perspective
    participant_index: int
    time_stamp: datetime
    patch_id: int | None
    battle_id: int | None
    kill_area: str | None
    player_id: str | None
    player_name: str | None
    guild_id: str | None
    guild_name: str | None
    alliance_id: str | None
    alliance_name: str | None
    average_item_power: float | None
    number_of_participants: int | None
    group_member_count: int | None
    total_victim_kill_fame: int | None
    kill_fame: int | None
    death_fame: int | None
    damage_done: float | None
    support_healing_done: float | None
    fame_ratio: float | None
    build_key: str | None
    slots: dict[str, str | None]


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _actor_identity(actor: Any) -> tuple[str | None, str | None] | None:
    if not isinstance(actor, dict):
        return None
    actor_id = _as_str(actor.get("Id"))
    actor_name = _as_str(actor.get("Name"))
    normalized_name = actor_name.strip().casefold() if actor_name else None
    if actor_id is None and normalized_name is None:
        return None
    return actor_id, normalized_name


def _slot_type(slot: Any) -> str | None:
    if not isinstance(slot, dict):
        return None
    value = slot.get("Type") or slot.get("type")
    return _as_str(value)


def extract_slot_types(actor: Any) -> dict[str, str | None]:
    if not isinstance(actor, dict):
        return {column: None for column in SLOT_COLUMNS}
    equipment = actor.get("Equipment")
    if not isinstance(equipment, dict):
        return {column: None for column in SLOT_COLUMNS}
    return {
        column: _slot_type(equipment.get(api_key))
        for column, api_key in SLOT_COLUMNS.items()
    }


def build_key_from_slots(slots: dict[str, str | None]) -> str | None:
    parts = [slots.get(column) or "" for column in CORE_BUILD_COLUMNS]
    if not any(parts):
        return None
    return "|".join(parts)


def _loadout_from_actor(
    *,
    source_region: str,
    event_id: int,
    time_stamp: datetime,
    patch_id: int | None,
    raw_event: dict[str, Any],
    actor: Any,
    perspective: Perspective,
    participant_index: int,
) -> EventLoadout | None:
    if not isinstance(actor, dict):
        return None

    slots = extract_slot_types(actor)
    return EventLoadout(
        source_region=source_region,
        event_id=event_id,
        perspective=perspective,
        participant_index=participant_index,
        time_stamp=time_stamp,
        patch_id=patch_id,
        battle_id=_as_int(raw_event.get("BattleId")),
        kill_area=_as_str(raw_event.get("KillArea")),
        player_id=_as_str(actor.get("Id")),
        player_name=_as_str(actor.get("Name")),
        guild_id=_as_str(actor.get("GuildId")),
        guild_name=_as_str(actor.get("GuildName")),
        alliance_id=_as_str(actor.get("AllianceId")),
        alliance_name=_as_str(actor.get("AllianceName")),
        average_item_power=_as_float(actor.get("AverageItemPower")),
        number_of_participants=_as_int(raw_event.get("NumberOfParticipants")),
        group_member_count=_as_int(raw_event.get("GroupMemberCount")),
        total_victim_kill_fame=_as_int(raw_event.get("TotalVictimKillFame")),
        kill_fame=_as_int(actor.get("KillFame")),
        death_fame=_as_int(actor.get("DeathFame")),
        damage_done=_as_float(actor.get("DamageDone")),
        support_healing_done=_as_float(actor.get("SupportHealingDone")),
        fame_ratio=_as_float(actor.get("FameRatio")),
        build_key=build_key_from_slots(slots),
        slots=slots,
    )


def extract_event_loadouts(
    *,
    source_region: str,
    event_id: int,
    time_stamp: datetime,
    patch_id: int | None,
    raw_event: dict[str, Any],
) -> list[EventLoadout]:
    """Return killer, victim, and participant loadout rows for one raw event."""
    rows: list[EventLoadout] = []
    killer_identity = _actor_identity(raw_event.get("Killer"))
    for perspective, key in (("killer", "Killer"), ("victim", "Victim")):
        row = _loadout_from_actor(
            source_region=source_region,
            event_id=event_id,
            time_stamp=time_stamp,
            patch_id=patch_id,
            raw_event=raw_event,
            actor=raw_event.get(key),
            perspective=perspective,
            participant_index=0,
        )
        if row is not None:
            rows.append(row)

    participants = raw_event.get("Participants")
    if isinstance(participants, list):
        seen_identities: set[tuple[str | None, str | None]] = set()
        for index, participant in enumerate(participants):
            identity = _actor_identity(participant)
            if identity is not None:
                if identity == killer_identity or identity in seen_identities:
                    continue
                seen_identities.add(identity)
            row = _loadout_from_actor(
                source_region=source_region,
                event_id=event_id,
                time_stamp=time_stamp,
                patch_id=patch_id,
                raw_event=raw_event,
                actor=participant,
                perspective="participant",
                participant_index=index,
            )
            if row is not None:
                rows.append(row)

    return rows
