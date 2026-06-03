"""Order domain model (FR-12 .. FR-16, FR-20)."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel

from app.models.common import MongoModel

OrderStatus = Literal["pending", "assigned", "delivering", "delivered", "failed"]


class Order(MongoModel):
    code: str
    address: str
    postal_code: str
    lat: float
    lng: float
    weight_kg: float
    required_by: str
    status: OrderStatus = "pending"
    cluster_id: Optional[str] = None
    driver_id: Optional[str] = None
    sequence: Optional[int] = None
    proof_photo: Optional[str] = None
    proof_signature: Optional[str] = None
    fail_reason: Optional[str] = None


class OrderIn(BaseModel):
    address: str
    postal_code: str
    lat: float
    lng: float
    weight_kg: float
    required_by: str


class OrderStatusIn(BaseModel):
    status: OrderStatus
    fail_reason: Optional[str] = None
    proof_photo: Optional[str] = None
    proof_signature: Optional[str] = None


class ManualAssignIn(BaseModel):
    driver_id: str
    order_ids: List[str]


class ClusterIn(BaseModel):
    max_distance_m: float = 2500.0
