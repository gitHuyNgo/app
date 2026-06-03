"""Vehicle domain model (FR-06 .. FR-08)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from app.models.common import MongoModel

VehicleType = Literal["motorbike", "van"]
FuelType = Literal["ev", "diesel"]


class Vehicle(MongoModel):
    plate: str
    type: VehicleType
    fuel_type: FuelType
    capacity_kg: float
    assigned_driver_id: Optional[str] = None


class VehicleIn(BaseModel):
    plate: str
    type: VehicleType
    fuel_type: FuelType
    capacity_kg: float


class AssignVehicleIn(BaseModel):
    driver_id: str
