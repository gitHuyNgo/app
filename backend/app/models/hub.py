"""Hub (delivery depot) domain model."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.models.common import MongoModel


class Hub(MongoModel):
    name: str
    address: str = ""
    lat: float
    lng: float
    is_default: bool = False
    notes: str = ""


class HubIn(BaseModel):
    name: str
    address: Optional[str] = ""
    lat: float
    lng: float
    is_default: Optional[bool] = False
    notes: Optional[str] = ""
