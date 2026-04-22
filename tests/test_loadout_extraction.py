from datetime import UTC, datetime

from albion_analytics.analysis.loadouts import (
    build_key_from_slots,
    extract_event_loadouts,
    extract_slot_types,
)


def test_extract_slot_types_accepts_type_aliases() -> None:
    slots = extract_slot_types(
        {
            "Equipment": {
                "MainHand": {"Type": "T8_MAIN_SWORD"},
                "Head": {"type": "T8_HEAD_LEATHER_SET1"},
            }
        }
    )

    assert slots["main_hand_type"] == "T8_MAIN_SWORD"
    assert slots["head_type"] == "T8_HEAD_LEATHER_SET1"
    assert slots["armor_type"] is None


def test_build_key_from_slots_returns_none_when_core_slots_empty() -> None:
    slots = {
        key: None
        for key in (
            "head_type",
            "armor_type",
            "shoes_type",
            "main_hand_type",
            "off_hand_type",
            "cape_type",
        )
    }

    assert build_key_from_slots(slots) is None


def test_extract_event_loadouts_returns_killer_victim_and_participants() -> None:
    raw = {
        "BattleId": 77,
        "KillArea": "Mists-Prime",
        "NumberOfParticipants": 2,
        "GroupMemberCount": 1,
        "TotalVictimKillFame": 1234,
        "Killer": {
            "Id": "killer-id",
            "Name": "Killer",
            "AverageItemPower": 1300.5,
            "DamageDone": 321.5,
            "SupportHealingDone": 99.0,
            "FameRatio": 0.5,
            "Equipment": {
                "MainHand": {"Type": "T8_MAIN_SWORD"},
                "Head": {"Type": "T8_HEAD_PLATE_SET1"},
                "Armor": {"Type": "T8_ARMOR_PLATE_SET1"},
                "Shoes": {"Type": "T8_SHOES_PLATE_SET1"},
                "Cape": {"Type": "T8_CAPE"},
            },
        },
        "Victim": {
            "Id": "victim-id",
            "Name": "Victim",
            "Equipment": {
                "MainHand": {"Type": "T7_MAIN_FIRESTAFF"},
            },
        },
        "Participants": [
            {
                "Id": "participant-id",
                "Name": "Participant",
                "KillFame": 10,
                "Equipment": {
                    "MainHand": {"Type": "T6_MAIN_BOW"},
                },
            }
        ],
    }

    rows = extract_event_loadouts(
        source_region="asia",
        event_id=1,
        time_stamp=datetime(2026, 4, 20, tzinfo=UTC),
        patch_id=None,
        raw_event=raw,
    )

    assert [row.perspective for row in rows] == ["killer", "victim", "participant"]
    assert rows[0].player_id == "killer-id"
    assert rows[0].battle_id == 77
    assert rows[0].kill_area == "Mists-Prime"
    assert rows[0].damage_done == 321.5
    assert rows[0].support_healing_done == 99.0
    assert rows[0].fame_ratio == 0.5
    assert rows[0].slots["main_hand_type"] == "T8_MAIN_SWORD"
    assert rows[0].build_key == (
        "T8_HEAD_PLATE_SET1|T8_ARMOR_PLATE_SET1|"
        "T8_SHOES_PLATE_SET1|T8_MAIN_SWORD||T8_CAPE"
    )
    assert rows[1].player_name == "Victim"
    assert rows[2].participant_index == 0
    assert rows[2].kill_fame == 10


def test_extract_event_loadouts_skips_killer_duplicate_in_participants() -> None:
    raw = {
        "Killer": {
            "Id": "killer-id",
            "Name": "Killer",
            "Equipment": {"MainHand": {"Type": "T8_MAIN_SWORD"}},
        },
        "Victim": {
            "Id": "victim-id",
            "Name": "Victim",
            "Equipment": {"MainHand": {"Type": "T7_MAIN_FIRESTAFF"}},
        },
        "Participants": [
            {
                "Id": "killer-id",
                "Name": "Killer",
                "Equipment": {"MainHand": {"Type": "T8_MAIN_SWORD"}},
            },
            {
                "Id": "participant-id",
                "Name": "Participant",
                "Equipment": {"MainHand": {"Type": "T6_MAIN_BOW"}},
            },
        ],
    }

    rows = extract_event_loadouts(
        source_region="asia",
        event_id=2,
        time_stamp=datetime(2026, 4, 20, tzinfo=UTC),
        patch_id=None,
        raw_event=raw,
    )

    assert [row.perspective for row in rows] == ["killer", "victim", "participant"]
    assert [row.player_id for row in rows] == ["killer-id", "victim-id", "participant-id"]
    assert rows[2].participant_index == 1
