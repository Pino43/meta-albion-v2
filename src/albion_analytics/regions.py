"""Gameinfo API base URLs per Albion server region."""

from __future__ import annotations

GAMEINFO_REGIONS: dict[str, str] = {
    "europe": "https://gameinfo.albiononline.com/api/gameinfo",
    "americas": "https://gameinfo-ams.albiononline.com/api/gameinfo",
    "asia": "https://gameinfo-sgp.albiononline.com/api/gameinfo",
}


def parse_region_filter(spec: str) -> list[str]:
    """Comma-separated region keys (e.g. 'europe,asia'). Empty means all."""
    parts = [p.strip().lower() for p in spec.split(",") if p.strip()]
    if not parts:
        return list(GAMEINFO_REGIONS.keys())
    unknown = [p for p in parts if p not in GAMEINFO_REGIONS]
    if unknown:
        raise ValueError(f"Unknown region(s): {unknown}. Valid: {list(GAMEINFO_REGIONS)}")
    return parts
