"""Cross-cutting helpers shared across routers and services."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.database import db


def new_id() -> str:
    """Generate a fresh UUID4 string."""
    return str(uuid.uuid4())


def now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


async def find_list(
    collection: str,
    query: Optional[Dict[str, Any]] = None,
    limit: int = 10_000,
) -> List[Dict[str, Any]]:
    """Return all documents in a collection matching ``query`` (without ``_id``)."""
    return await db[collection].find(query or {}, {"_id": 0}).to_list(limit)


async def find_one(collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the first document matching ``query`` (without ``_id``)."""
    return await db[collection].find_one(query, {"_id": 0})


async def unique_phone(
    collection: str,
    phone: str,
    exclude_id: Optional[str] = None,
) -> bool:
    """Return ``True`` when ``phone`` is free in ``collection`` (optionally excluding one record)."""
    query: Dict[str, Any] = {"phone": phone}
    if exclude_id:
        query["id"] = {"$ne": exclude_id}
    return await db[collection].find_one(query, {"_id": 0}) is None
