"""Zone domain model (FR-09 .. FR-11)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from app.models.common import MongoModel


class Zone(MongoModel):
    name: str
    polygon: List[List[float]]  # [[lat, lng], ...]
    center: List[float]
    driver_ids: List[str] = []
    color: str = "#0ea5a4"


class ZoneIn(BaseModel):
    name: str
    polygon: List[List[float]]
    color: Optional[str] = "#0ea5a4"


class AssignDriverZoneIn(BaseModel):
    driver_id: str
