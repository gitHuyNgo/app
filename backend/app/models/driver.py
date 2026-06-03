"""Driver domain model (FR-03 .. FR-05, FR-18)."""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel

from app.models.common import MongoModel

DriverStatus = Literal["available", "delivering", "off_duty"]
LicenseType = Literal["A", "B", "C"]


class Driver(MongoModel):
    name: str
    phone: str
    license_type: LicenseType = "B"
    status: DriverStatus = "available"
    vehicle_id: Optional[str] = None
    zone_id: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    hub_manager_id: Optional[str] = None


class DriverIn(BaseModel):
    name: str
    phone: str
    license_type: LicenseType = "B"
    hub_manager_id: Optional[str] = None


class DriverStatusIn(BaseModel):
    status: DriverStatus


class LocationIn(BaseModel):
    lat: float
    lng: float
