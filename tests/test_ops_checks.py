from datetime import UTC, datetime, timedelta

from albion_analytics.ops.checks import Thresholds, bytes_from_gb, classify_ops_snapshot


def snapshot(
    *,
    database_bytes: int,
    latest_status: str = "success",
    finished_age_seconds: int = 60,
) -> dict:
    now = datetime(2026, 4, 21, 12, 0, tzinfo=UTC)
    return {
        "database": {"name": "albion", "bytes": database_bytes},
        "tables": [],
        "latest_collector_run": {
            "id": 1,
            "started_at": now - timedelta(seconds=finished_age_seconds + 5),
            "finished_at": now - timedelta(seconds=finished_age_seconds),
            "status": latest_status,
            "error_message": None,
        },
    }


def thresholds() -> Thresholds:
    return Thresholds(
        db_warning_bytes=bytes_from_gb(40),
        db_critical_bytes=bytes_from_gb(48),
        collector_max_age_seconds=600,
    )


def test_classify_ops_snapshot_ok() -> None:
    report = classify_ops_snapshot(
        snapshot(database_bytes=bytes_from_gb(10)),
        ready_ok=True,
        thresholds=thresholds(),
        now=datetime(2026, 4, 21, 12, 0, tzinfo=UTC),
    )

    assert report["status"] == "ok"


def test_classify_ops_snapshot_warns_on_database_size() -> None:
    report = classify_ops_snapshot(
        snapshot(database_bytes=bytes_from_gb(42)),
        ready_ok=True,
        thresholds=thresholds(),
        now=datetime(2026, 4, 21, 12, 0, tzinfo=UTC),
    )

    assert report["status"] == "warning"


def test_classify_ops_snapshot_critical_on_ready_failure() -> None:
    report = classify_ops_snapshot(
        snapshot(database_bytes=bytes_from_gb(10)),
        ready_ok=False,
        thresholds=thresholds(),
        now=datetime(2026, 4, 21, 12, 0, tzinfo=UTC),
    )

    assert report["status"] == "critical"


def test_classify_ops_snapshot_warns_on_stale_collector() -> None:
    report = classify_ops_snapshot(
        snapshot(database_bytes=bytes_from_gb(10), finished_age_seconds=1200),
        ready_ok=True,
        thresholds=thresholds(),
        now=datetime(2026, 4, 21, 12, 0, tzinfo=UTC),
    )

    assert report["status"] == "warning"
