"""Driver CRUD + status / location endpoints (FR-03 .. FR-05, FR-18)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from app.database import db
from app.models.driver import Driver, DriverIn, DriverStatusIn, LocationIn
from app.utils import find_list, now_iso, unique_phone

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.post("", response_model=Driver)
async def create_driver(data: DriverIn) -> Driver:
    if not await unique_phone("drivers", data.phone):
        raise HTTPException(status_code=400, detail="Phone already exists")
    driver = Driver(**data.model_dump())
    await db.drivers.insert_one(driver.model_dump())
    return driver


@router.get("", response_model=List[Driver])
async def list_drivers() -> List[dict]:
    return await find_list("drivers")


@router.get("/locations")
async def list_driver_locations() -> List[dict]:
    """Compact projection of all drivers that have a GPS fix."""
    drivers = await find_list("drivers")
    return [
        {
            "id": d["id"],
            "name": d["name"],
            "status": d["status"],
            "location": d.get("location"),
            "vehicle_id": d.get("vehicle_id"),
            "zone_id": d.get("zone_id"),
        }
        for d in drivers
        if d.get("location")
    ]


@router.put("/{driver_id}", response_model=Driver)
async def update_driver(driver_id: str, data: DriverIn) -> dict:
    if not await unique_phone("drivers", data.phone, exclude_id=driver_id):
        raise HTTPException(status_code=400, detail="Phone already exists")
    res = await db.drivers.find_one_and_update(
        {"id": driver_id},
        {"$set": data.model_dump()},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return res


@router.delete("/{driver_id}")
async def delete_driver(driver_id: str) -> dict:
    await db.vehicles.update_many(
        {"assigned_driver_id": driver_id},
        {"$set": {"assigned_driver_id": None}},
    )
    await db.zones.update_many({}, {"$pull": {"driver_ids": driver_id}})
    await db.drivers.delete_one({"id": driver_id})
    return {"ok": True}


@router.put("/{driver_id}/status")
async def update_driver_status(driver_id: str, body: DriverStatusIn) -> dict:
    res = await db.drivers.find_one_and_update(
        {"id": driver_id},
        {"$set": {"status": body.status}},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return res


@router.put("/{driver_id}/location")
async def update_driver_location(driver_id: str, body: LocationIn) -> dict:
    location = {"lat": body.lat, "lng": body.lng, "updated_at": now_iso()}
    res = await db.drivers.find_one_and_update(
        {"id": driver_id},
        {"$set": {"location": location}},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return res
