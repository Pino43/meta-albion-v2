"""FastAPI app for read-only ranking and collector status endpoints."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from hmac import compare_digest
from typing import Annotated, Any, Literal

import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg_pool import AsyncConnectionPool

from albion_analytics.config import Settings, get_settings
from albion_analytics.storage.aggregates_repo import (
    SLOT_TO_COLUMN,
    fetch_build_rankings,
    fetch_item_rankings,
)
from albion_analytics.storage.status_repo import (
    CORE_STATUS_TABLES,
    check_core_tables,
    fetch_api_status,
)

Perspective = Literal["killer", "victim", "participant"]
Region = Literal["europe", "americas", "asia"]
Connector = Callable[[Settings], Awaitable[psycopg.AsyncConnection]]


@dataclass
class CacheEntry:
    expires_at: float
    value: Any


class TTLCache:
    def __init__(self, ttl_sec: float) -> None:
        self._ttl_sec = ttl_sec
        self._entries: dict[tuple[Any, ...], CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get_or_set(
        self,
        key: tuple[Any, ...],
        loader: Callable[[], Awaitable[Any]],
    ) -> Any:
        if self._ttl_sec <= 0:
            return await loader()

        now = time.monotonic()
        async with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry.expires_at > now:
                return entry.value

        value = await loader()
        async with self._lock:
            self._entries[key] = CacheEntry(
                expires_at=time.monotonic() + self._ttl_sec,
                value=value,
            )
        return value


class FixedWindowRateLimiter:
    def __init__(self, *, window_sec: float = 60.0) -> None:
        self._window_sec = window_sec
        self._buckets: dict[str, tuple[float, int]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str, *, limit: int) -> bool:
        if limit <= 0:
            return True

        now = time.monotonic()
        async with self._lock:
            window_start, count = self._buckets.get(key, (now, 0))
            if now - window_start >= self._window_sec:
                self._buckets[key] = (now, 1)
                return True
            if count >= limit:
                return False
            self._buckets[key] = (window_start, count + 1)
            return True


async def _get_pool(request: Request) -> AsyncConnectionPool:
    pool: AsyncConnectionPool | None = getattr(request.app.state, "db_pool", None)
    if pool is not None:
        return pool

    settings: Settings = request.app.state.settings
    if not settings.database_url:
        raise ValueError("DATABASE_URL is not set")

    async with request.app.state.pool_lock:
        pool = getattr(request.app.state, "db_pool", None)
        if pool is not None:
            return pool

        pool = AsyncConnectionPool(
            conninfo=settings.database_url,
            min_size=settings.api_db_pool_min_size,
            max_size=settings.api_db_pool_max_size,
            open=False,
        )
        await pool.open(wait=True)
        request.app.state.db_pool = pool
        return pool


@asynccontextmanager
async def _db_connection(request: Request) -> AsyncIterator[psycopg.AsyncConnection]:
    connector: Connector | None = request.app.state.connect_database
    settings: Settings = request.app.state.settings
    if connector is not None:
        conn = await connector(settings)
        try:
            yield conn
        finally:
            await conn.close()
        return

    pool = await _get_pool(request)
    async with pool.connection() as conn:
        yield conn


def _validate_slot(slot: str) -> str:
    if slot not in SLOT_TO_COLUMN:
        allowed = ", ".join(sorted(SLOT_TO_COLUMN))
        raise HTTPException(
            status_code=422,
            detail=f"slot must be one of: {allowed}",
        )
    return slot


def _client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _authorize_admin(request: Request) -> None:
    settings: Settings = request.app.state.settings
    if settings.api_status_public:
        return

    expected = settings.api_admin_token
    if not expected:
        raise HTTPException(status_code=404, detail="not_found")

    value = request.headers.get("authorization", "")
    prefix = "Bearer "
    if not value.startswith(prefix):
        raise HTTPException(status_code=401, detail="unauthorized")
    token = value[len(prefix) :]
    if not compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="unauthorized")


def _parse_cors_origins(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _ranking_meta(
    *,
    settings: Settings,
    **values: Any,
) -> dict[str, Any]:
    return {
        **values,
        "generated_at": datetime.now(UTC).isoformat(),
        "cache_ttl_sec": settings.api_cache_ttl_sec,
    }


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        pool: AsyncConnectionPool | None = getattr(app.state, "db_pool", None)
        if pool is not None:
            await pool.close()


def create_app(
    *,
    settings: Settings | None = None,
    connector: Connector | None = None,
) -> FastAPI:
    s = settings or get_settings()
    app = FastAPI(
        title="Albion Analytics API",
        version="0.1.0",
        description="Read-only rankings and collector status for Albion Analytics.",
        docs_url="/docs" if s.api_docs_enabled else None,
        redoc_url="/redoc" if s.api_docs_enabled else None,
        openapi_url="/openapi.json" if s.api_docs_enabled else None,
        lifespan=_lifespan,
    )
    cors_origins = _parse_cors_origins(s.api_cors_allow_origins)
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["GET", "OPTIONS"],
            allow_headers=["authorization", "content-type"],
            max_age=600,
        )

    app.state.settings = s
    app.state.connect_database = connector
    app.state.db_pool = None
    app.state.pool_lock = asyncio.Lock()
    app.state.cache = TTLCache(s.api_cache_ttl_sec)
    app.state.rate_limiter = FixedWindowRateLimiter()
    app.state.check_core_tables = check_core_tables
    app.state.fetch_api_status = fetch_api_status
    app.state.fetch_item_rankings = fetch_item_rankings
    app.state.fetch_build_rankings = fetch_build_rankings

    @app.middleware("http")
    async def rate_limit(request: Request, call_next: Callable[[Request], Awaitable[Any]]) -> Any:
        if request.url.path != "/health":
            allowed = await request.app.state.rate_limiter.allow(
                f"{_client_key(request)}:{request.url.path}",
                limit=request.app.state.settings.api_rate_limit_per_minute,
            )
            if not allowed:
                return JSONResponse(status_code=429, content={"detail": "rate_limited"})
        return await call_next(request)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready(request: Request) -> dict[str, Any]:
        try:
            async with _db_connection(request) as conn:
                missing = await request.app.state.check_core_tables(conn)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"status": "not_ready"},
            ) from exc

        if missing:
            raise HTTPException(
                status_code=503,
                detail={"status": "not_ready"},
            )
        return {"status": "ready", "tables": list(CORE_STATUS_TABLES)}

    @app.get("/v1/status")
    async def status(request: Request) -> dict[str, Any]:
        _authorize_admin(request)
        async with _db_connection(request) as conn:
            data = await request.app.state.fetch_api_status(conn)
        return {"data": data, "meta": {"tables": list(CORE_STATUS_TABLES)}}

    @app.get("/v1/rankings/items")
    async def item_rankings(
        request: Request,
        slot: Annotated[str, Query(description="Equipment slot to rank")],
        days: Annotated[int, Query(ge=1, le=30)] = 7,
        region: Region | None = None,
        perspective: Perspective = "killer",
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> dict[str, Any]:
        slot = _validate_slot(slot)

        async def load_rows() -> list[dict[str, Any]]:
            async with _db_connection(request) as conn:
                return await request.app.state.fetch_item_rankings(
                    conn,
                    slot=slot,
                    perspective=perspective,
                    days=days,
                    region=region,
                    limit=limit,
                )

        rows = await request.app.state.cache.get_or_set(
            ("items", slot, perspective, days, region, limit),
            load_rows,
        )
        return {
            "data": rows,
            "meta": _ranking_meta(
                settings=request.app.state.settings,
                slot=slot,
                days=days,
                region=region,
                perspective=perspective,
                limit=limit,
            ),
        }

    @app.get("/v1/rankings/builds")
    async def build_rankings(
        request: Request,
        days: Annotated[int, Query(ge=1, le=30)] = 7,
        region: Region | None = None,
        perspective: Perspective = "killer",
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> dict[str, Any]:
        async def load_rows() -> list[dict[str, Any]]:
            async with _db_connection(request) as conn:
                return await request.app.state.fetch_build_rankings(
                    conn,
                    perspective=perspective,
                    days=days,
                    region=region,
                    limit=limit,
                )

        rows = await request.app.state.cache.get_or_set(
            ("builds", perspective, days, region, limit),
            load_rows,
        )
        return {
            "data": rows,
            "meta": _ranking_meta(
                settings=request.app.state.settings,
                days=days,
                region=region,
                perspective=perspective,
                limit=limit,
            ),
        }

    return app


app = create_app()
