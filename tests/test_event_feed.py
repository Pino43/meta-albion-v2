from __future__ import annotations

from typing import Any

import pytest

from albion_analytics.ingestion.event_feed import _fetch_new_events


class FakeEventsClient:
    def __init__(self, pages: dict[int, list[dict[str, Any]]]) -> None:
        self.pages = pages
        self.calls: list[tuple[int, int]] = []

    async def get_recent_events(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        self.calls.append((limit, offset))
        return self.pages.get(offset, [])


@pytest.mark.asyncio
async def test_fetch_new_events_stops_at_cursor() -> None:
    client = FakeEventsClient(
        {
            0: [
                {"EventId": 105},
                {"EventId": 104},
                {"EventId": 100},
                {"EventId": 99},
            ]
        }
    )

    rows = await _fetch_new_events(
        client,  # type: ignore[arg-type]
        page_size=4,
        max_pages=10,
        cursor_event_id=100,
    )

    assert [row["EventId"] for row in rows] == [105, 104]
    assert client.calls == [(4, 0)]


@pytest.mark.asyncio
async def test_fetch_new_events_honors_max_pages() -> None:
    client = FakeEventsClient(
        {
            0: [{"EventId": 3}],
            1: [{"EventId": 2}],
            2: [{"EventId": 1}],
        }
    )

    rows = await _fetch_new_events(
        client,  # type: ignore[arg-type]
        page_size=1,
        max_pages=2,
        cursor_event_id=None,
    )

    assert [row["EventId"] for row in rows] == [3, 2]
    assert client.calls == [(1, 0), (1, 1)]


@pytest.mark.asyncio
async def test_fetch_new_events_empty_response() -> None:
    client = FakeEventsClient({0: []})

    rows = await _fetch_new_events(
        client,  # type: ignore[arg-type]
        page_size=10,
        max_pages=10,
        cursor_event_id=None,
    )

    assert rows == []
    assert client.calls == [(10, 0)]


@pytest.mark.asyncio
async def test_fetch_new_events_ignores_invalid_event_id_for_cursor_comparison() -> None:
    client = FakeEventsClient(
        {
            0: [
                {"EventId": "not-an-int"},
                {"EventId": 101},
                {"EventId": 100},
            ]
        }
    )

    rows = await _fetch_new_events(
        client,  # type: ignore[arg-type]
        page_size=3,
        max_pages=10,
        cursor_event_id=100,
    )

    assert [row["EventId"] for row in rows] == ["not-an-int", 101]
