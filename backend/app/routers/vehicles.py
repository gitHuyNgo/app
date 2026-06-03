"""Vehicle CRUD + driver assignment endpoints (FR-06 .. FR-08)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from app.database import db
from app.models.vehicle import AssignVehicleIn, Vehicle, VehicleIn
from app.utils import find_list, find_one

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post("", response_model=Vehicle)
async def create_vehicle(data: VehicleIn) -> Vehicle:
    vehicle = Vehicle(**data.model_dump())
    await db.vehicles.insert_one(vehicle.model_dump())
    return vehicle


@router.get("", response_model=List[Vehicle])
async def list_vehicles() -> List[dict]:
    return await find_list("vehicles")


@router.delete("/{vehicle_id}")
async def delete_vehicle(vehicle_id: str) -> dict:
    vehicle = await find_one("vehicles", {"id": vehicle_id})
    if vehicle and vehicle.get("assigned_driver_id"):
        await db.drivers.update_one(
            {"id": vehicle["assigned_driver_id"]},
            {"$set": {"vehicle_id": None}},
        )
    await db.vehicles.delete_one({"id": vehicle_id})
    return {"ok": True}


@router.post("/{vehicle_id}/assign")
async def assign_vehicle(vehicle_id: str, body: AssignVehicleIn) -> dict:
    vehicle = await find_one("vehicles", {"id": vehicle_id})
    driver = await find_one("drivers", {"id": body.driver_id})
    if not vehicle or not driver:
        raise HTTPException(status_code=404, detail="Vehicle or driver not found")

    # Enforce "one driver per vehicle" — unassign previous links on both sides.
    if driver.get("vehicle_id"):
        await db.vehicles.update_one(
            {"id": driver["vehicle_id"]},
            {"$set": {"assigned_driver_id": None}},
        )
    if vehicle.get("assigned_driver_id"):
        await db.drivers.update_one(
            {"id": vehicle["assigned_driver_id"]},
            {"$set": {"vehicle_id": None}},
        )

    await db.vehicles.update_one(
        {"id": vehicle_id},
        {"$set": {"assigned_driver_id": body.driver_id}},
    )
    await db.drivers.update_one(
        {"id": body.driver_id},
        {"$set": {"vehicle_id": vehicle_id}},
    )
    return {"ok": True}


@router.post("/{vehicle_id}/unassign")
async def unassign_vehicle(vehicle_id: str) -> dict:
    vehicle = await find_one("vehicles", {"id": vehicle_id})
    if vehicle and vehicle.get("assigned_driver_id"):
        await db.drivers.update_one(
            {"id": vehicle["assigned_driver_id"]},
            {"$set": {"vehicle_id": None}},
        )
    await db.vehicles.update_one(
        {"id": vehicle_id},
        {"$set": {"assigned_driver_id": None}},
    )
    return {"ok": True}
