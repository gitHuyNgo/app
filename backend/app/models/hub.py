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
    color: str = "#0d7c78"
    notes: str = ""


class HubIn(BaseModel):
    name: str
    address: Optional[str] = ""
    lat: float
    lng: float
    is_default: Optional[bool] = False
    color: Optional[str] = "#0d7c78"
    notes: Optional[str] = ""
