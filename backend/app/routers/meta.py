"""Meta-endpoints: service health, statistics, demo seed."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from app.database import db
from app.seed import seed_demo
from app.services.hubs import get_active_hub

router = APIRouter(tags=["meta"])


@router.get("/")
async def root() -> Dict[str, Any]:
    """Service identity + active hub (used as a health-check)."""
    return {"service": "LionCity AI-Logistics", "hub": await get_active_hub()}


@router.get("/stats")
async def stats() -> Dict[str, int]:
    """Aggregated counts for the dashboard."""
    return {
        "hub_managers": await db.hub_managers.count_documents({}),
        "drivers": await db.drivers.count_documents({}),
        "drivers_available": await db.drivers.count_documents({"status": "available"}),
        "drivers_delivering": await db.drivers.count_documents({"status": "delivering"}),
        "vehicles": await db.vehicles.count_documents({}),
        "vehicles_ev": await db.vehicles.count_documents({"fuel_type": "ev"}),
        "zones": await db.zones.count_documents({}),
        "orders_pending": await db.orders.count_documents({"status": "pending"}),
        "orders_assigned": await db.orders.count_documents({"status": "assigned"}),
        "orders_delivering": await db.orders.count_documents({"status": "delivering"}),
        "orders_delivered": await db.orders.count_documents({"status": "delivered"}),
        "orders_failed": await db.orders.count_documents({"status": "failed"}),
        "clusters": await db.clusters.count_documents({}),
    }


@router.post("/seed")
async def seed() -> Dict[str, Any]:
    """Wipe and repopulate the database with demo data."""
    return await seed_demo()
