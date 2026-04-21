"""Kill event models — align fields with live API responses as you integrate."""

from __future__ import annotations

from datetime import datetime

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
    kill_fame: int | None = Field(None, alias="KillFame")
    death_fame: int | None = Field(None, alias="DeathFame")
    damage_done: float | None = Field(None, alias="DamageDone")
    support_healing_done: float | None = Field(None, alias="SupportHealingDone")
    fame_ratio: float | None = Field(None, alias="FameRatio")


class Participant(BaseModel):
    """A player who contributed to a kill event."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str | None = Field(None, alias="Id")
    name: str | None = Field(None, alias="Name")
    guild_id: str | None = Field(None, alias="GuildId")
    guild_name: str | None = Field(None, alias="GuildName")
    alliance_id: str | None = Field(None, alias="AllianceId")
    alliance_name: str | None = Field(None, alias="AllianceName")
    average_item_power: float | None = Field(None, alias="AverageItemPower")
    equipment: Equipment | None = Field(None, alias="Equipment")
    damage_done: float | None = Field(None, alias="DamageDone")
    support_healing_done: float | None = Field(None, alias="SupportHealingDone")
    kill_fame: int | None = Field(None, alias="KillFame")
    death_fame: int | None = Field(None, alias="DeathFame")
    fame_ratio: float | None = Field(None, alias="FameRatio")


class KillEvent(BaseModel):
    """One killboard event (killer defeated victim)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    event_id: int | None = Field(None, alias="EventId")
    time_stamp: datetime | None = Field(None, alias="TimeStamp")
    # API 페이로드 스키마 버전(게임 패치 아님). 패치는 TimeStamp + game_patches 구간으로 매핑.
    api_payload_version: int | None = Field(None, alias="Version")
    killer: PlayerBrief | None = Field(None, alias="Killer")
    victim: PlayerBrief | None = Field(None, alias="Victim")
    number_of_participants: int | None = Field(None, alias="NumberOfParticipants")
    group_member_count: int | None = Field(None, alias="GroupMemberCount")
    total_victim_kill_fame: int | None = Field(None, alias="TotalVictimKillFame")
    total_victim_loot_fame: int | None = Field(None, alias="TotalVictimLootFame")
    participants: list[Participant] | None = Field(None, alias="Participants")
    battle_id: int | None = Field(None, alias="BattleId")
    kill_area: str | None = Field(None, alias="KillArea")
    event_type: str | None = Field(None, alias="Type")
