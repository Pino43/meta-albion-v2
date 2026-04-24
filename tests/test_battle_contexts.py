from __future__ import annotations

import inspect

from albion_analytics.storage import battle_contexts_repo
from albion_analytics.storage.battle_contexts_repo import (
    battle_player_count,
    parse_battle_context,
)


def test_parse_battle_context_counts_players_object() -> None:
    context = parse_battle_context(
        source_region="asia",
        payload={
            "id": 123,
            "startTime": "2026-04-23T20:19:00.095719600Z",
            "endTime": "2026-04-23T20:21:58.440453700Z",
            "totalFame": 812005,
            "totalKills": 9,
            "clusterName": "Cluster",
            "players": {"one": {}, "two": {}, "three": {}},
        },
    )

    assert context is not None
    assert context.battle_id == 123
    assert context.player_count == 3
    assert context.total_fame == 812005
    assert context.total_kills == 9
    assert context.cluster_name == "Cluster"


def test_battle_player_count_accepts_object_list_or_missing() -> None:
    assert battle_player_count({"players": {"a": {}, "b": {}}}) == 2
    assert battle_player_count({"players": [{}, {}, {}]}) == 3
    assert battle_player_count({}) == 0


def test_battle_context_upsert_is_idempotent_sql() -> None:
    source = inspect.getsource(battle_contexts_repo.upsert_battle_contexts)

    assert "ON CONFLICT (source_region, battle_id) DO UPDATE" in source
    assert "player_count = EXCLUDED.player_count" in source


def test_pending_battle_refs_only_uses_classified_event_contexts() -> None:
    source = inspect.getsource(battle_contexts_repo.fetch_pending_battle_refs)

    assert "FROM event_contexts ec" in source
    assert "JOIN kill_events ke" in source
    assert "ec.scale_source IS DISTINCT FROM 'battle_players'" in source


def test_battle_context_application_updates_scale_columns() -> None:
    source = inspect.getsource(battle_contexts_repo.apply_battle_contexts_to_event_contexts)

    assert "battle_player_count = eb.player_count" in source
    assert "scale_source = 'battle_players'" in source
    assert "WHEN bc.player_count <= 10 THEN 'party'" in source
    assert "WHEN bc.player_count <= 20 THEN 'large_party'" in source
    assert "ELSE 'zvz'" in source


def test_event_participant_scale_source_backfill_is_null_only() -> None:
    source = inspect.getsource(battle_contexts_repo.backfill_event_participant_scale_source)

    assert "SET scale_source = 'event_participants'" in source
    assert "WHERE scale_source IS NULL" in source
