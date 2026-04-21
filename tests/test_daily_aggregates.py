from datetime import UTC, datetime

import pytest

from albion_analytics.scripts.ranking_items import positive_int
from albion_analytics.storage.aggregates_repo import (
    build_build_usage_aggregate_sql,
    build_item_usage_aggregate_sql,
    build_ranking_builds_sql,
    build_ranking_items_sql,
    utc_day_lower_bound,
)
from albion_analytics.storage.outcomes_repo import (
    build_build_outcome_aggregate_sql,
    build_item_outcome_aggregate_sql,
)


def test_item_aggregate_sql_uses_selected_slot_column() -> None:
    sql = build_item_usage_aggregate_sql("main_hand")

    assert "main_hand_type AS item_type" in sql
    assert "ON CONFLICT (day, source_region, perspective, slot, item_type)" in sql
    assert "IS DISTINCT FROM" in sql


def test_build_aggregate_sql_requires_build_key() -> None:
    sql = build_build_usage_aggregate_sql()

    assert "build_key IS NOT NULL" in sql
    assert "build_key <> ''" in sql
    assert "ON CONFLICT (day, source_region, perspective, build_key)" in sql
    assert "IS DISTINCT FROM" in sql


def test_item_outcome_aggregate_sql_uses_event_contexts_and_shared_credit() -> None:
    sql = build_item_outcome_aggregate_sql("main_hand")

    assert "JOIN event_contexts" in sql
    assert "1.0 / GREATEST(ec.observed_kill_side_count, 1)" in sql
    assert "ON CONFLICT (" in sql
    assert "daily_item_outcomes" in sql


def test_build_outcome_aggregate_sql_requires_build_key_and_shared_credit() -> None:
    sql = build_build_outcome_aggregate_sql()

    assert "JOIN event_contexts" in sql
    assert "el.build_key IS NOT NULL" in sql
    assert "1.0 / GREATEST(ec.observed_kill_side_count, 1)" in sql


def test_utc_day_lower_bound_includes_today_as_one_day() -> None:
    now = datetime(2026, 4, 20, 23, 30, tzinfo=UTC)

    assert utc_day_lower_bound(1, now=now).isoformat() == "2026-04-20"
    assert utc_day_lower_bound(7, now=now).isoformat() == "2026-04-14"


def test_utc_day_lower_bound_rejects_non_positive_days() -> None:
    with pytest.raises(ValueError, match="days"):
        utc_day_lower_bound(0)


def test_ranking_sql_adds_region_filter_only_when_requested() -> None:
    item_with_region = build_ranking_items_sql(region="asia")
    item_without_region = build_ranking_items_sql(region=None)
    build_with_region = build_ranking_builds_sql(region="asia")
    build_without_region = build_ranking_builds_sql(region=None)

    assert "source_region = %s" in item_with_region
    assert "source_region = %s" not in item_without_region
    assert "source_region = %s" in build_with_region
    assert "source_region = %s" not in build_without_region


def test_positive_int_validation() -> None:
    assert positive_int("7") == 7
    with pytest.raises(Exception, match="must be >= 1"):
        positive_int("0")
