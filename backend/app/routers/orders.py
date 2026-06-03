"""Order CRUD, clustering and assignment endpoints (FR-12 .. FR-16, FR-20)."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.database import db
from app.models.order import ClusterIn, ManualAssignIn, Order, OrderIn, OrderStatusIn
from app.services.assignment import assign_clusters_to_drivers
from app.services.clustering import cluster_pending_orders
from app.utils import find_list, find_one

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=Order)
async def create_order(data: OrderIn) -> Order:
    count = await db.orders.count_documents({})
    order = Order(code=f"ORD-{count + 1:05d}", **data.model_dump())
    await db.orders.insert_one(order.model_dump())
    return order


@router.get("", response_model=List[Order])
async def list_orders(
    status: Optional[str] = None,
    driver_id: Optional[str] = None,
) -> List[dict]:
    query: dict = {}
    if status:
        query["status"] = status
    if driver_id:
        query["driver_id"] = driver_id
    return await find_list("orders", query)


@router.delete("/{order_id}")
async def delete_order(order_id: str) -> dict:
    await db.orders.delete_one({"id": order_id})
    return {"ok": True}


@router.put("/{order_id}/status")
async def update_order_status(order_id: str, body: OrderStatusIn) -> dict:
    updates: dict = {"status": body.status}
    if body.fail_reason:
        updates["fail_reason"] = body.fail_reason
    if body.proof_photo:
        updates["proof_photo"] = body.proof_photo
    if body.proof_signature:
        updates["proof_signature"] = body.proof_signature
    res = await db.orders.find_one_and_update(
        {"id": order_id},
        {"$set": updates},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return res


@router.post("/cluster")
async def run_clustering(body: ClusterIn) -> dict:
    return await cluster_pending_orders(body.max_distance_m)


@router.post("/assign-auto")
async def run_auto_assignment() -> dict:
    return await assign_clusters_to_drivers()


@router.post("/assign-manual")
async def run_manual_assignment(body: ManualAssignIn) -> dict:
    driver = await find_one("drivers", {"id": body.driver_id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    await db.orders.update_many(
        {"id": {"$in": body.order_ids}},
        {"$set": {"driver_id": body.driver_id, "status": "assigned"}},
    )
    return {"ok": True, "assigned": len(body.order_ids)}
