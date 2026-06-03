"""Shared base model for documents persisted to MongoDB."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.utils import new_id, now_iso


class MongoModel(BaseModel):
    """Base for any persisted entity with an ``id`` and ``created_at``."""

    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_iso)
