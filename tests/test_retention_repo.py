from datetime import UTC, datetime

import pytest

from albion_analytics.scripts.cleanup_retention import positive_int
from albion_analytics.storage.retention_repo import (
    retention_datetime_cutoff,
    retention_day_cutoff,
)


def test_retention_datetime_cutoff_uses_utc_rolling_window() -> None:
    now = datetime(2026, 4, 20, 12, 30, tzinfo=UTC)

    assert retention_datetime_cutoff(10, now=now).isoformat() == "2026-04-10T12:30:00+00:00"


def test_retention_day_cutoff_keeps_today_as_one_day() -> None:
    now = datetime(2026, 4, 20, 23, 30, tzinfo=UTC)

    assert retention_day_cutoff(1, now=now).isoformat() == "2026-04-20"
    assert retention_day_cutoff(90, now=now).isoformat() == "2026-01-21"


def test_retention_cutoffs_reject_non_positive_days() -> None:
    with pytest.raises(ValueError, match="retention days"):
        retention_datetime_cutoff(0)
    with pytest.raises(ValueError, match="retention days"):
        retention_day_cutoff(0)


def test_cleanup_cli_positive_int_validation() -> None:
    assert positive_int("30") == 30
    with pytest.raises(Exception, match="must be >= 1"):
        positive_int("0")
