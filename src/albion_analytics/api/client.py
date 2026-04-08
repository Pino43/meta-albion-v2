"""HTTP client for Albion Gameinfo API with simple rate limiting."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from albion_analytics.config import get_settings


class GameinfoClient:
    """Thin async client around the community-used Gameinfo base URL."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        rate_limit_per_sec: float | None = None,
        timeout_sec: float | None = None,
    ) -> None:
        s = get_settings()
        self._base = (base_url or s.albion_gameinfo_base_url).rstrip("/")
        self._min_interval = 1.0 / (rate_limit_per_sec or s.albion_rate_limit_per_sec)
        self._timeout = timeout_sec or s.albion_http_timeout_sec
        self._last_request_at = 0.0
        self._lock = asyncio.Lock()

    async def _throttle(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_request_at)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_at = time.monotonic()

    async def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        await self._throttle()
        url = f"{self._base}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def search_players(self, query: str) -> list[dict[str, Any]]:
        data = await self.get_json("search", params={"q": query})
        if isinstance(data, dict) and "players" in data:
            return list(data["players"])
        if isinstance(data, list):
            return data
        return []

    async def get_player_kills(
        self,
        player_id: str,
        *,
        limit: int = 51,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        data = await self.get_json(
            f"players/{player_id}/kills",
            params={"limit": limit, "offset": offset},
        )
        if isinstance(data, list):
            return data
        return []
