"""Cluster domain model (FR-13)."""
from __future__ import annotations

from typing import List

from app.models.common import MongoModel


class Cluster(MongoModel):
    label: str
    order_ids: List[str]
    centroid: List[float]
