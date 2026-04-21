from datetime import UTC, datetime

from albion_analytics.analysis.event_contexts import (
    bucket_fight_scale,
    build_event_context,
    classify_content_type,
    normalize_kill_area_slug,
)


def test_normalize_kill_area_slug_collapses_case_and_symbols() -> None:
    assert normalize_kill_area_slug(" Mist Prime / 1 ") == "mist_prime_1"


def test_classify_content_type_uses_prefix_heuristics() -> None:
    assert classify_content_type("corrupted_alpha") == "corrupted_dungeon"
    assert classify_content_type("mist_highlands") == "mists"
    assert classify_content_type("hellgate_red") == "hellgate"
    assert classify_content_type("road_to_avalon") == "roads"
    assert classify_content_type("depths_lower") == "abyssal"
    assert classify_content_type("bridgewatch") == "unknown"


def test_bucket_fight_scale_uses_fixed_ranges() -> None:
    assert bucket_fight_scale(1) == "solo"
    assert bucket_fight_scale(2) == "duo"
    assert bucket_fight_scale(5) == "small_party"
    assert bucket_fight_scale(10) == "party"
    assert bucket_fight_scale(20) == "large_party"
    assert bucket_fight_scale(21) == "zvz"
    assert bucket_fight_scale(None) == "unknown"


def test_build_event_context_falls_back_to_observed_participant_count() -> None:
    context = build_event_context(
        source_region="asia",
        event_id=10,
        time_stamp=datetime(2026, 4, 20, tzinfo=UTC),
        raw_event={
            "KillArea": "Mist Prime",
            "Participants": [{}, {}],
        },
    )

    assert context.kill_area_slug == "mist_prime"
    assert context.content_type == "mists"
    assert context.observed_kill_side_count == 3
    assert context.reported_participant_count == 3
    assert context.fight_scale_bucket == "small_party"
