"""Zone CRUD + driver assignment endpoints (FR-09 .. FR-11)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from app.database import db
from app.models.zone import AssignDriverZoneIn, Zone, ZoneIn
from app.services.geo import polygon_centroid
from app.utils import find_list, find_one

router = APIRouter(prefix="/zones", tags=["zones"])


@router.post("", response_model=Zone)
async def create_zone(data: ZoneIn) -> Zone:
    zone = Zone(center=polygon_centroid(data.polygon), **data.model_dump())
    await db.zones.insert_one(zone.model_dump())
    return zone


@router.get("", response_model=List[Zone])
async def list_zones() -> List[dict]:
    return await find_list("zones")


@router.put("/{zone_id}", response_model=Zone)
async def update_zone(zone_id: str, data: ZoneIn) -> dict:
    updates = data.model_dump()
    updates["center"] = polygon_centroid(data.polygon)
    res = await db.zones.find_one_and_update(
        {"id": zone_id},
        {"$set": updates},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return res


@router.delete("/{zone_id}")
async def delete_zone(zone_id: str) -> dict:
    await db.drivers.update_many({"zone_id": zone_id}, {"$set": {"zone_id": None}})
    await db.zones.delete_one({"id": zone_id})
    return {"ok": True}


@router.post("/{zone_id}/assign-driver")
async def assign_driver_to_zone(zone_id: str, body: AssignDriverZoneIn) -> dict:
    zone = await find_one("zones", {"id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    await db.zones.update_many({}, {"$pull": {"driver_ids": body.driver_id}})
    await db.zones.update_one({"id": zone_id}, {"$addToSet": {"driver_ids": body.driver_id}})
    await db.drivers.update_one({"id": body.driver_id}, {"$set": {"zone_id": zone_id}})
    return {"ok": True}


@router.post("/{zone_id}/unassign-driver")
async def unassign_driver_from_zone(zone_id: str, body: AssignDriverZoneIn) -> dict:
    await db.zones.update_one({"id": zone_id}, {"$pull": {"driver_ids": body.driver_id}})
    await db.drivers.update_one({"id": body.driver_id}, {"$set": {"zone_id": None}})
    return {"ok": True}
