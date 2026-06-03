"""Aggregated API router — combines every resource under ``/api``."""
from __future__ import annotations

from fastapi import APIRouter

from app.routers import (
    clusters,
    drivers,
    hub_managers,
    hubs,
    lta,
    meta,
    orders,
    routing,
    shipper,
    vehicles,
    zones,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(meta.router)
api_router.include_router(hubs.router)
api_router.include_router(hub_managers.router)
api_router.include_router(drivers.router)
api_router.include_router(vehicles.router)
api_router.include_router(zones.router)
api_router.include_router(orders.router)
api_router.include_router(clusters.router)
api_router.include_router(routing.router)
api_router.include_router(shipper.router)
api_router.include_router(lta.router)

__all__ = ["api_router"]
