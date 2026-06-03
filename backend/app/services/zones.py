"""Zone helpers: resolve a (lat, lng) point to a zone."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.services.geo import haversine, point_in_polygon
from app.utils import find_list


async def find_zone_for_point(lat: float, lng: float, zones: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """Return the id of the zone that contains the point, or the nearest one by centroid.

    ``zones`` may be passed in to avoid repeated DB hits when resolving in bulk.
    """
    if zones is None:
        zones = await find_list("zones")
    if not zones:
        return None

    # 1. Direct containment.
    for zone in zones:
        if point_in_polygon((lat, lng), zone["polygon"]):
            return zone["id"]

    # 2. Fallback to nearest zone by centroid distance.
    nearest = min(
        zones,
        key=lambda z: haversine((lat, lng), (z["center"][0], z["center"][1])),
    )
    return nearest["id"]
