"""FastAPI entrypoint for LionCity AI-Logistics.

This module is intentionally tiny: it wires together the lifespan, CORS, and
the aggregated ``api_router`` from :mod:`app.routers`. All business logic lives
under the :mod:`app` package.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app import logging as _logging  # noqa: F401 — initialise root logger
from app.config import settings
from app.database import close_db
from app.routers import api_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: nothing to start, close MongoDB on shutdown."""
    yield
    await close_db()


def create_app() -> FastAPI:
    """Build the FastAPI instance — kept separate to ease testing."""
    app = FastAPI(
        title="LionCity AI-Logistics",
        description="Hub & Delivery Coordination System backend (FR-01 .. FR-20).",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
