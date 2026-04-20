"""HTTP client for Albion Gameinfo API with simple rate limiting."""

from __future__ import annotations

import asyncio
import email.utils
import time
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

import httpx

from albion_analytics.config import get_settings


class GameinfoClient:
    """Thin async client around the community-used Gameinfo base URL.

    Use as an async context manager to share one TCP connection pool::

        async with GameinfoClient() as client:
            events = await client.get_recent_events()

    Or call ``aclose()`` manually when done.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        rate_limit_per_sec: float | None = None,
        timeout_sec: float | None = None,
        max_retries: int | None = None,
        retry_base_delay_sec: float | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        s = get_settings()
        self._base = (base_url or s.albion_gameinfo_base_url).rstrip("/")
        rate_limit = (
            s.albion_rate_limit_per_sec if rate_limit_per_sec is None else rate_limit_per_sec
        )
        self._min_interval = 0.0 if rate_limit <= 0 else 1.0 / rate_limit
        self._timeout = timeout_sec or s.albion_http_timeout_sec
        self._max_retries = s.albion_http_max_retries if max_retries is None else max_retries
        self._retry_base_delay_sec = (
            s.albion_http_retry_base_delay_sec
            if retry_base_delay_sec is None
            else retry_base_delay_sec
        )
        self._last_request_at = 0.0
        self._lock = asyncio.Lock()
        self._http = httpx.AsyncClient(timeout=self._timeout, transport=transport)

    async def __aenter__(self) -> GameinfoClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _throttle(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_request_at)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_at = time.monotonic()

    async def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base}/{path.lstrip('/')}"
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                await self._throttle()
                resp = await self._http.get(url, params=params)
                if self._should_retry_response(resp) and attempt < self._max_retries:
                    await self._sleep_before_retry(attempt, resp)
                    continue
                resp.raise_for_status()
                return resp.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt >= self._max_retries:
                    raise
                await self._sleep_before_retry(attempt)

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Gameinfo request failed without an exception")

    @staticmethod
    def _should_retry_response(resp: httpx.Response) -> bool:
        return resp.status_code == 429 or 500 <= resp.status_code <= 599

    async def _sleep_before_retry(
        self,
        attempt: int,
        resp: httpx.Response | None = None,
    ) -> None:
        delay = self._retry_after_delay(resp)
        if delay is None:
            delay = self._retry_base_delay_sec * (2**attempt)
        if delay > 0:
            await asyncio.sleep(delay)

    @staticmethod
    def _retry_after_delay(resp: httpx.Response | None) -> float | None:
        if resp is None:
            return None
        value = resp.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = email.utils.parsedate_to_datetime(value)
            except (TypeError, ValueError):
                return None
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())

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

    async def get_recent_events(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Recent killboard events for this Gameinfo region (global feed, not per-player)."""
        data = await self.get_json("events", params={"limit": limit, "offset": offset})
        if isinstance(data, list):
            return data
        return []
