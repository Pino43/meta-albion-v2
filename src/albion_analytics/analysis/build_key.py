"""Normalize head/chest/shoes/weapon/cape into a hashable build key."""

from __future__ import annotations

from albion_analytics.models import PlayerBrief


def _slot_type(equipment: object | None, attr: str) -> str | None:
    if equipment is None:
        return None
    slot = getattr(equipment, attr, None)
    if slot is None:
        return None
    return getattr(slot, "type", None)


def build_fingerprint_from_victim(victim: PlayerBrief | None) -> tuple[str, ...] | None:
    """
    Main build fingerprint: (head, chest, shoes, main_hand, off_hand, cape).

    Uses victim loadout — typical for 'what builds get killed' style stats.
    Swap to killer when analyzing outgoing kills.
    """
    if victim is None or victim.equipment is None:
        return None
    eq = victim.equipment
    return (
        _slot_type(eq, "head") or "",
        _slot_type(eq, "armor") or "",
        _slot_type(eq, "shoes") or "",
        _slot_type(eq, "main_hand") or "",
        _slot_type(eq, "off_hand") or "",
        _slot_type(eq, "cape") or "",
    )
