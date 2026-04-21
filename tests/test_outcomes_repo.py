from albion_analytics.storage.outcomes_repo import (
    _baseline_rate,
    _confidence_label,
    _scored_row,
    build_key_slot_value,
    parse_build_key,
)


def test_parse_build_key_and_slot_lookup_cover_core_slots() -> None:
    build_key = "HEAD|ARMOR|SHOES|MAIN|OFF|CAPE"

    assert parse_build_key(build_key) == {
        "head_type": "HEAD",
        "armor_type": "ARMOR",
        "shoes_type": "SHOES",
        "main_hand_type": "MAIN",
        "off_hand_type": "OFF",
        "cape_type": "CAPE",
    }
    assert build_key_slot_value(build_key, "main_hand") == "MAIN"
    assert build_key_slot_value(build_key, "cape") == "CAPE"
    assert build_key_slot_value(build_key, "bag") is None


def test_scored_row_uses_smoothed_adjusted_score_and_confidence() -> None:
    rows = [
        {
            "item_type": "A",
            "kill_credit": 8.0,
            "death_count": 2.0,
            "appearance_count": 10,
            "event_count": 10,
            "avg_item_power": 1200.0,
            "total_kill_fame": 100,
        },
        {
            "item_type": "B",
            "kill_credit": 2.0,
            "death_count": 8.0,
            "appearance_count": 5,
            "event_count": 5,
            "avg_item_power": 1100.0,
            "total_kill_fame": 50,
        },
    ]
    baseline = _baseline_rate(rows)

    scored = _scored_row(rows[0], baseline_rate=baseline, total_appearance_count=15)

    assert round(baseline, 4) == 0.5
    assert round(scored["kill_side_rate"], 4) == 0.8
    assert round(scored["kd_ratio"], 4) == 4.0
    assert round(scored["sample"], 4) == 10.0
    assert round(scored["pick_rate"], 4) == 0.6667
    assert round(scored["adjusted_score"], 4) == 0.0857
    assert scored["confidence"] == "low"


def test_confidence_label_uses_fixed_buckets() -> None:
    assert _confidence_label(0) == "low"
    assert _confidence_label(25) == "medium"
    assert _confidence_label(100) == "high"
