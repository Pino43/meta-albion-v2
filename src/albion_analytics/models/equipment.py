"""Equipment slots as returned by Gameinfo kill/death payloads."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class EquipmentSlot(BaseModel):
    """Single equipped item (nullable in API when empty)."""

    model_config = ConfigDict(extra="ignore")

    type: str | None = Field(None, validation_alias=AliasChoices("Type", "type"))
    count: int | None = None
    quality: int | None = None
    active_spells: list[Any] | None = None
    passive_spells: list[Any] | None = None


class Equipment(BaseModel):
    """Full loadout on a player in a kill event."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    main_hand: EquipmentSlot | None = Field(None, alias="MainHand")
    off_hand: EquipmentSlot | None = Field(None, alias="OffHand")
    head: EquipmentSlot | None = Field(None, alias="Head")
    armor: EquipmentSlot | None = Field(None, alias="Armor")
    shoes: EquipmentSlot | None = Field(None, alias="Shoes")
    bag: EquipmentSlot | None = Field(None, alias="Bag")
    cape: EquipmentSlot | None = Field(None, alias="Cape")
    mount: EquipmentSlot | None = Field(None, alias="Mount")
    potion: EquipmentSlot | None = Field(None, alias="Potion")
    food: EquipmentSlot | None = Field(None, alias="Food")
