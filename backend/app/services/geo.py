"""Geospatial primitives shared across services."""
from __future__ import annotations

import math
from typing import List, Tuple

EARTH_RADIUS_M = 6_371_000.0
SG_CENTER: Tuple[float, float] = (1.3521, 103.8198)

# Bounding box approximating Singapore's CBD / ERP-heavy zone.
CBD_BBOX = {
    "min_lat": 1.270, "max_lat": 1.305,
    "min_lng": 103.830, "max_lng": 103.870,
}


def haversine(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Great-circle distance in metres between two (lat, lng) points."""
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def polygon_centroid(polygon: List[List[float]]) -> List[float]:
    """Naive centroid (mean of vertex coordinates). Falls back to SG centre."""
    if not polygon:
        return list(SG_CENTER)
    lat = sum(p[0] for p in polygon) / len(polygon)
    lng = sum(p[1] for p in polygon) / len(polygon)
    return [lat, lng]


def in_cbd(lat: float, lng: float) -> bool:
    """Return ``True`` when a (lat, lng) lies inside the CBD bounding box."""
    return (CBD_BBOX["min_lat"] <= lat <= CBD_BBOX["max_lat"]
            and CBD_BBOX["min_lng"] <= lng <= CBD_BBOX["max_lng"])


def interpolate(
    a: Tuple[float, float],
    b: Tuple[float, float],
    steps: int = 12,
) -> List[List[float]]:
    """Linear interpolation between two points; returns ``steps`` evenly spaced points."""
    return [
        [a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps]
        for i in range(steps)
    ]
