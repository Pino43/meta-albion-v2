from albion_analytics.analysis import build_fingerprint_from_victim
from albion_analytics.models import Equipment, EquipmentSlot, PlayerBrief


def test_build_fingerprint_from_victim() -> None:
    v = PlayerBrief(
        Id="x",
        Name="v",
        Equipment=Equipment(
            Head=EquipmentSlot(type="HEAD_T4"),
            Armor=EquipmentSlot(type="ARMOR_T4"),
            Shoes=EquipmentSlot(type="SHOES_T4"),
            MainHand=EquipmentSlot(type="MAIN_T4"),
            OffHand=EquipmentSlot(type="OFF_T4"),
            Cape=EquipmentSlot(type="CAPE_T4"),
        ),
    )
    fp = build_fingerprint_from_victim(v)
    assert fp == ("HEAD_T4", "ARMOR_T4", "SHOES_T4", "MAIN_T4", "OFF_T4", "CAPE_T4")
