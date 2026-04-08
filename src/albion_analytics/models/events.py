"""Kill event models — align fields with live API responses as you integrate."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from albion_analytics.models.equipment import Equipment


class PlayerBrief(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str | None = Field(None, alias="Id")
    name: str | None = Field(None, alias="Name")
    guild_id: str | None = Field(None, alias="GuildId")
    guild_name: str | None = Field(None, alias="GuildName")
    alliance_id: str | None = Field(None, alias="AllianceId")
    alliance_name: str | None = Field(None, alias="AllianceName")
    average_item_power: float | None = Field(None, alias="AverageItemPower")
    equipment: Equipment | None = Field(None, alias="Equipment")


class KillEvent(BaseModel):
    """One killboard event (killer defeated victim)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event_id: int | None = Field(None, alias="EventId")
    killer: PlayerBrief | None = Field(None, alias="Killer")
    victim: PlayerBrief | None = Field(None, alias="Victim")
    number_of_participants: int | None = Field(None, alias="NumberOfParticipants")
    group_member_count: int | None = Field(None, alias="GroupMemberCount")
    total_victim_kill_fame: int | None = Field(None, alias="TotalVictimKillFame")
    total_victim_loot_fame: int | None = Field(None, alias="TotalVictimLootFame")
    participants: list[dict[str, Any]] | None = None
