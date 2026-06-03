"""Shipper-facing endpoints (FR-19)."""
from __future__ import annotations

from fastapi import APIRouter

from app.utils import find_list, find_one

router = APIRouter(prefix="/shipper", tags=["shipper"])


@router.get("/{driver_id}/orders")
async def shipper_inbox(driver_id: str) -> dict:
    """Return the driver's active orders (in optimal sequence) and their route."""
    orders = await find_list("orders", {
        "driver_id": driver_id,
        "status": {"$in": ["assigned", "delivering"]},
    })
    orders.sort(key=lambda o: (o.get("sequence") or 9999))
    route = await find_one("routes", {"driver_id": driver_id})
    return {"orders": orders, "route": route}
