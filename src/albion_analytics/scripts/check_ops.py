"""Check collector/API/storage operational health."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

import httpx

from albion_analytics.config import get_settings
from albion_analytics.ops.checks import Thresholds, bytes_from_gb, classify_ops_snapshot
from albion_analytics.storage.db import connect_database
from albion_analytics.storage.ops_repo import fetch_ops_snapshot


async def _check_ready(url: str | None) -> bool | None:
    if not url:
        return None
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
        except httpx.HTTPError:
            return False
    return resp.status_code == 200


async def _send_webhook(url: str | None, payload: dict[str, Any]) -> None:
    if not url:
        return
    status = payload.get("status", "unknown")
    issue_count = len(
        [
            check
            for check in payload.get("checks", [])
            if isinstance(check, dict) and check.get("status") != "ok"
        ]
    )
    summary = f"Albion Analytics ops status: {status} ({issue_count} issue(s))"
    message = {
        "content": summary,
        "text": summary,
        "payload": payload,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(url, json=message)


async def _run(
    *,
    ready_url: str | None,
    webhook_url: str | None,
    db_warning_gb: float,
    db_critical_gb: float,
    collector_max_age_minutes: int,
) -> int:
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1

    conn = await connect_database(s)
    try:
        snapshot = await fetch_ops_snapshot(conn)
    finally:
        await conn.close()

    ready_ok = await _check_ready(ready_url or s.ops_ready_url)
    report = classify_ops_snapshot(
        snapshot,
        ready_ok=ready_ok,
        thresholds=Thresholds(
            db_warning_bytes=bytes_from_gb(db_warning_gb),
            db_critical_bytes=bytes_from_gb(db_critical_gb),
            collector_max_age_seconds=collector_max_age_minutes * 60,
        ),
    )

    await _send_webhook(webhook_url or s.ops_webhook_url, report)
    print(json.dumps(report, ensure_ascii=False, default=str, indent=2))
    return 2 if report["status"] == "critical" else 0


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def main() -> None:
    s = get_settings()
    p = argparse.ArgumentParser(description="Check Albion Analytics operational health")
    p.add_argument("--ready-url", default=s.ops_ready_url)
    p.add_argument("--webhook-url", default=s.ops_webhook_url)
    p.add_argument("--db-warning-gb", type=positive_float, default=s.ops_db_warning_gb)
    p.add_argument("--db-critical-gb", type=positive_float, default=s.ops_db_critical_gb)
    p.add_argument(
        "--collector-max-age-minutes",
        type=positive_int,
        default=s.ops_collector_max_age_minutes,
    )
    args = p.parse_args()
    raise SystemExit(
        asyncio.run(
            _run(
                ready_url=args.ready_url,
                webhook_url=args.webhook_url,
                db_warning_gb=args.db_warning_gb,
                db_critical_gb=args.db_critical_gb,
                collector_max_age_minutes=args.collector_max_age_minutes,
            )
        )
    )


if __name__ == "__main__":
    main()
