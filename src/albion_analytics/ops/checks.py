"""Classify operational snapshots into actionable health states."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

Status = Literal["ok", "warning", "critical"]


@dataclass(frozen=True)
class Thresholds:
    db_warning_bytes: int
    db_critical_bytes: int
    collector_max_age_seconds: int


def bytes_from_gb(value: float) -> int:
    return int(value * 1024 * 1024 * 1024)


def worst_status(values: list[Status]) -> Status:
    if "critical" in values:
        return "critical"
    if "warning" in values:
        return "warning"
    return "ok"


def classify_ops_snapshot(
    snapshot: dict[str, Any],
    *,
    ready_ok: bool | None,
    thresholds: Thresholds,
    now: datetime | None = None,
) -> dict[str, Any]:
    ref = now or datetime.now(UTC)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)

    checks: list[dict[str, Any]] = []
    database_bytes = int(snapshot.get("database", {}).get("bytes") or 0)
    db_status: Status = "ok"
    if database_bytes >= thresholds.db_critical_bytes:
        db_status = "critical"
    elif database_bytes >= thresholds.db_warning_bytes:
        db_status = "warning"
    checks.append(
        {
            "name": "database_size",
            "status": db_status,
            "value_bytes": database_bytes,
            "warning_bytes": thresholds.db_warning_bytes,
            "critical_bytes": thresholds.db_critical_bytes,
        }
    )

    latest_run = snapshot.get("latest_collector_run")
    collector_status: Status = "critical"
    collector_age_seconds: float | None = None
    if latest_run:
        finished_at = latest_run.get("finished_at") or latest_run.get("started_at")
        if finished_at is not None:
            if isinstance(finished_at, str):
                finished_at = datetime.fromisoformat(finished_at)
            if finished_at.tzinfo is None:
                finished_at = finished_at.replace(tzinfo=UTC)
            collector_age_seconds = (ref - finished_at.astimezone(UTC)).total_seconds()
        if latest_run.get("status") == "success" and (
            collector_age_seconds is None
            or collector_age_seconds <= thresholds.collector_max_age_seconds
        ):
            collector_status = "ok"
        elif latest_run.get("status") == "success":
            collector_status = "warning"
    checks.append(
        {
            "name": "collector_freshness",
            "status": collector_status,
            "age_seconds": collector_age_seconds,
            "max_age_seconds": thresholds.collector_max_age_seconds,
            "latest_status": latest_run.get("status") if latest_run else None,
        }
    )

    if ready_ok is not None:
        checks.append(
            {
                "name": "api_ready",
                "status": "ok" if ready_ok else "critical",
                "ready": ready_ok,
            }
        )

    return {
        "status": worst_status([check["status"] for check in checks]),
        "checked_at": ref.isoformat(),
        "checks": checks,
        "snapshot": snapshot,
    }
