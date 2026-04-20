"""FastAPI app for read-only ranking and collector status endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Literal

import psycopg
from fastapi import FastAPI, HTTPException, Query, Request

from albion_analytics.config import Settings, get_settings
from albion_analytics.storage.aggregates_repo import (
    SLOT_TO_COLUMN,
    fetch_build_rankings,
    fetch_item_rankings,
)
from albion_analytics.storage.db import connect_database
from albion_analytics.storage.status_repo import (
    CORE_STATUS_TABLES,
    check_core_tables,
    fetch_api_status,
)

Perspective = Literal["killer", "victim", "participant"]
Region = Literal["europe", "americas", "asia"]
Connector = Callable[[Settings], Awaitable[psycopg.AsyncConnection]]


async def _connect(request: Request) -> psycopg.AsyncConnection:
    connector: Connector = request.app.state.connect_database
    settings: Settings = request.app.state.settings
    return await connector(settings)


def _validate_slot(slot: str) -> str:
    if slot not in SLOT_TO_COLUMN:
        allowed = ", ".join(sorted(SLOT_TO_COLUMN))
        raise HTTPException(
            status_code=422,
            detail=f"slot must be one of: {allowed}",
        )
    return slot


def create_app(
    *,
    settings: Settings | None = None,
    connector: Connector = connect_database,
) -> FastAPI:
    app = FastAPI(
        title="Albion Analytics API",
        version="0.1.0",
        description="Read-only rankings and collector status for Albion Analytics.",
    )
    app.state.settings = settings or get_settings()
    app.state.connect_database = connector
    app.state.check_core_tables = check_core_tables
    app.state.fetch_api_status = fetch_api_status
    app.state.fetch_item_rankings = fetch_item_rankings
    app.state.fetch_build_rankings = fetch_build_rankings

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready(request: Request) -> dict[str, Any]:
        try:
            conn = await _connect(request)
            try:
                missing = await request.app.state.check_core_tables(conn)
            finally:
                await conn.close()
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"status": "not_ready", "error": str(exc)},
            ) from exc

        if missing:
            raise HTTPException(
                status_code=503,
                detail={"status": "not_ready", "missing_tables": missing},
            )
        return {"status": "ready", "tables": list(CORE_STATUS_TABLES)}

    @app.get("/v1/status")
    async def status(request: Request) -> dict[str, Any]:
        conn = await _connect(request)
        try:
            data = await request.app.state.fetch_api_status(conn)
        finally:
            await conn.close()
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
        conn = await _connect(request)
        try:
            rows = await request.app.state.fetch_item_rankings(
                conn,
                slot=slot,
                perspective=perspective,
                days=days,
                region=region,
                limit=limit,
            )
        finally:
            await conn.close()
        return {
            "data": rows,
            "meta": {
                "slot": slot,
                "days": days,
                "region": region,
                "perspective": perspective,
                "limit": limit,
            },
        }

    @app.get("/v1/rankings/builds")
    async def build_rankings(
        request: Request,
        days: Annotated[int, Query(ge=1, le=30)] = 7,
        region: Region | None = None,
        perspective: Perspective = "killer",
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> dict[str, Any]:
        conn = await _connect(request)
        try:
            rows = await request.app.state.fetch_build_rankings(
                conn,
                perspective=perspective,
                days=days,
                region=region,
                limit=limit,
            )
        finally:
            await conn.close()
        return {
            "data": rows,
            "meta": {
                "days": days,
                "region": region,
                "perspective": perspective,
                "limit": limit,
            },
        }

    return app


app = create_app()
