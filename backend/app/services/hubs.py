"""Hub resolution helpers."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.utils import find_one

DEFAULT_HUB: Dict[str, Any] = {
    "id": "default",
    "name": "Central Singapore Hub",
    "lat": 1.3521,
    "lng": 103.8198,
}


async def get_active_hub(hub_id: Optional[str] = None) -> Dict[str, Any]:
    """Resolve which hub to use as routing/assignment origin.

    Order of precedence:
        1. ``hub_id`` explicitly passed by the caller (if it exists).
        2. The hub flagged ``is_default``.
        3. The first hub in the collection.
        4. A hard-coded fallback at Singapore's centroid.
    """
    if hub_id:
        explicit = await find_one("hubs", {"id": hub_id})
        if explicit:
            return explicit

    default = await find_one("hubs", {"is_default": True})
    if default:
        return default

    any_hub = await db.hubs.find_one({}, {"_id": 0})
    return any_hub or DEFAULT_HUB
