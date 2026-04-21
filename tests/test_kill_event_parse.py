from albion_analytics.models import KillEvent


def test_kill_event_minimal_json() -> None:
    raw = {
        "EventId": 1,
        "BattleId": 99,
        "KillArea": "Corrupted-Alpha",
        "Killer": {
            "Id": "k1",
            "Name": "K",
            "DamageDone": 123.4,
            "SupportHealingDone": 55.0,
            "FameRatio": 0.25,
        },
        "Victim": {
            "Id": "v1",
            "Name": "V",
            "Equipment": {
                "MainHand": {"type": "MAIN"},
                "Head": {"type": "HEAD"},
            },
        },
    }
    ev = KillEvent.model_validate(raw)
    assert ev.event_id == 1
    assert ev.killer and ev.killer.name == "K"
    assert ev.killer and ev.killer.damage_done == 123.4
    assert ev.battle_id == 99
    assert ev.kill_area == "Corrupted-Alpha"
    assert ev.victim and ev.victim.equipment
    assert ev.victim.equipment.main_hand and ev.victim.equipment.main_hand.type == "MAIN"
