"""Hub Manager domain model (FR-01 / FR-02)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from app.models.common import MongoModel

HubManagerStatus = Literal["available", "off_duty"]


class HubManager(MongoModel):
    name: str
    phone: str
    status: HubManagerStatus = "available"
    hub_name: Optional[str] = None


class HubManagerIn(BaseModel):
    name: str
    phone: str
    status: Optional[HubManagerStatus] = "available"
    hub_name: Optional[str] = None
