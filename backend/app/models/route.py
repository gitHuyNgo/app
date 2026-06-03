"""Route record + routing request schemas (FR-17, FR-18)."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel

from app.models.common import MongoModel

RouteMode = Literal["time", "eco", "avoid_erp"]


class RouteRecord(MongoModel):
    driver_id: str
    mode: RouteMode
    waypoints: List[List[float]]
    ordered_order_ids: List[str]
    distance_m: float
    duration_s: float
    geometry: List[List[float]]


class RoutePlanIn(BaseModel):
    driver_id: str
    mode: RouteMode = "time"
    hub_id: Optional[str] = None


class SimulateStepIn(BaseModel):
    step_m: float = 200.0
