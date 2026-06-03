"""Cluster domain model (FR-13)."""
from __future__ import annotations

from typing import List, Optional

from app.models.common import MongoModel


class Cluster(MongoModel):
    label: str
    order_ids: List[str]
    centroid: List[float]
    total_weight_kg: float = 0.0
    zone_id: Optional[str] = None
