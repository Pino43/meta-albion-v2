from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from albion_analytics.config import Settings
from albion_analytics.server.app import create_app


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


async def fake_connector(_settings: Settings) -> FakeConnection:
    return FakeConnection()


def make_client() -> TestClient:
    app = create_app(
        settings=Settings(database_url="postgresql://example"),
        connector=fake_connector,
    )
    return TestClient(app)


def test_health_does_not_require_database() -> None:
    async def exploding_connector(_settings: Settings) -> FakeConnection:
        raise AssertionError("health should not open the database")

    app = create_app(settings=Settings(database_url=None), connector=exploding_connector)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ready_when_core_tables_exist() -> None:
    client = make_client()

    async def fake_check_core_tables(_conn: FakeConnection) -> list[str]:
        return []

    client.app.state.check_core_tables = fake_check_core_tables

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_returns_503_when_core_tables_are_missing() -> None:
    client = make_client()

    async def fake_check_core_tables(_conn: FakeConnection) -> list[str]:
        return ["daily_item_usage"]

    client.app.state.check_core_tables = fake_check_core_tables

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["missing_tables"] == ["daily_item_usage"]


def test_status_returns_counts_and_latest_run() -> None:
    client = make_client()

    async def fake_status(_conn: FakeConnection) -> dict[str, Any]:
        return {
            "tables": {
                "kill_events": 10,
                "event_loadouts": 20,
                "daily_item_usage": 30,
                "daily_build_usage": 40,
            },
            "latest_collector_run": {
                "id": 7,
                "started_at": datetime(2026, 4, 20, 1, 2, tzinfo=UTC),
                "finished_at": datetime(2026, 4, 20, 1, 3, tzinfo=UTC),
                "status": "success",
            },
        }

    client.app.state.fetch_api_status = fake_status

    response = client.get("/v1/status")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["tables"]["daily_item_usage"] == 30
    assert body["data"]["latest_collector_run"]["id"] == 7
    assert body["meta"]["tables"] == [
        "kill_events",
        "event_loadouts",
        "daily_item_usage",
        "daily_build_usage",
    ]


def test_item_rankings_passes_validated_defaults_to_reader() -> None:
    client = make_client()
    seen: dict[str, Any] = {}

    async def fake_items(
        _conn: FakeConnection,
        *,
        slot: str,
        perspective: str,
        days: int,
        region: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        seen.update(
            {
                "slot": slot,
                "perspective": perspective,
                "days": days,
                "region": region,
                "limit": limit,
            }
        )
        return [{"item_type": "T4_MAIN_SWORD", "uses": 3}]

    client.app.state.fetch_item_rankings = fake_items

    response = client.get("/v1/rankings/items?slot=main_hand&region=asia")

    assert response.status_code == 200
    assert seen == {
        "slot": "main_hand",
        "perspective": "killer",
        "days": 7,
        "region": "asia",
        "limit": 20,
    }
    assert response.json()["data"] == [{"item_type": "T4_MAIN_SWORD", "uses": 3}]


def test_item_rankings_rejects_bad_slot_days_and_limit() -> None:
    client = make_client()

    assert client.get("/v1/rankings/items?slot=bad").status_code == 422
    assert client.get("/v1/rankings/items?slot=main_hand&days=31").status_code == 422
    assert client.get("/v1/rankings/items?slot=main_hand&limit=101").status_code == 422


def test_build_rankings_passes_validated_params_to_reader() -> None:
    client = make_client()
    seen: dict[str, Any] = {}

    async def fake_builds(
        _conn: FakeConnection,
        *,
        perspective: str,
        days: int,
        region: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        seen.update(
            {
                "perspective": perspective,
                "days": days,
                "region": region,
                "limit": limit,
            }
        )
        return [{"build_key": "head|armor|shoes|weapon", "uses": 4}]

    client.app.state.fetch_build_rankings = fake_builds

    response = client.get(
        "/v1/rankings/builds?perspective=participant&days=3&region=europe&limit=5"
    )

    assert response.status_code == 200
    assert seen == {
        "perspective": "participant",
        "days": 3,
        "region": "europe",
        "limit": 5,
    }
    assert response.json()["meta"] == {
        "days": 3,
        "region": "europe",
        "perspective": "participant",
        "limit": 5,
    }


def test_build_rankings_rejects_invalid_perspective_days_and_limit() -> None:
    client = make_client()

    assert client.get("/v1/rankings/builds?perspective=bad").status_code == 422
    assert client.get("/v1/rankings/builds?days=0").status_code == 422
    assert client.get("/v1/rankings/builds?limit=0").status_code == 422
