from __future__ import annotations

import httpx
import pytest

from albion_analytics.api.client import GameinfoClient


@pytest.mark.asyncio
async def test_get_json_retries_500_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    async with GameinfoClient(
        base_url="https://gameinfo.test",
        rate_limit_per_sec=0,
        max_retries=1,
        retry_base_delay_sec=0,
        transport=httpx.MockTransport(handler),
    ) as client:
        data = await client.get_json("events")

    assert data == {"ok": True}
    assert calls == 2


@pytest.mark.asyncio
async def test_get_json_retries_429_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"}, request=request)
        return httpx.Response(200, json=[{"EventId": 1}], request=request)

    async with GameinfoClient(
        base_url="https://gameinfo.test",
        rate_limit_per_sec=0,
        max_retries=1,
        retry_base_delay_sec=0,
        transport=httpx.MockTransport(handler),
    ) as client:
        data = await client.get_json("events")

    assert data == [{"EventId": 1}]
    assert calls == 2


@pytest.mark.asyncio
async def test_get_json_raises_after_timeout_retries() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("timeout", request=request)

    async with GameinfoClient(
        base_url="https://gameinfo.test",
        rate_limit_per_sec=0,
        max_retries=1,
        retry_base_delay_sec=0,
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(httpx.ConnectTimeout):
            await client.get_json("events")

    assert calls == 2


@pytest.mark.asyncio
async def test_get_battle_uses_battle_endpoint() -> None:
    seen_path = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_path
        seen_path = request.url.path
        return httpx.Response(200, json={"id": 123, "players": {"a": {}, "b": {}}}, request=request)

    async with GameinfoClient(
        base_url="https://gameinfo.test/api/gameinfo",
        rate_limit_per_sec=0,
        transport=httpx.MockTransport(handler),
    ) as client:
        data = await client.get_battle(123)

    assert seen_path == "/api/gameinfo/battles/123"
    assert data["id"] == 123
