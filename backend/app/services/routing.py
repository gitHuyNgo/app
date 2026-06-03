"""Routing engine — OSRM with a deterministic Python fallback.

The fallback is used whenever OSRM is unreachable or rate-limited.
It implements a nearest-neighbour TSP heuristic with a CBD detour for the
``avoid_erp`` mode and naive linear interpolation for the geometry.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.logging import logger
from app.services.geo import CBD_BBOX, haversine, in_cbd, interpolate

OSRM_TIMEOUT_S = 3
URBAN_SPEED_MPS_DEFAULT = 8.5
URBAN_SPEED_MPS_ECO = 9.7


def _osrm_coord_str(coords: List[Tuple[float, float]]) -> str:
    return ";".join(f"{lng},{lat}" for lat, lng in coords)


async def osrm_route(
    coords: List[Tuple[float, float]],
    *,
    alternatives: bool = False,
) -> Optional[Dict[str, Any]]:
    """Call OSRM ``/route``; return parsed JSON or ``None`` if unreachable."""
    if len(coords) < 2:
        return None
    params = {
        "overview": "full",
        "geometries": "geojson",
        "alternatives": str(alternatives).lower(),
        "steps": "false",
    }
    url = f"{settings.osrm_base_url}/route/v1/driving/{_osrm_coord_str(coords)}"
    try:
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT_S) as client:
            r = await client.get(url, params=params)
            return r.json() if r.status_code == 200 else None
    except Exception as exc:
        logger.info("OSRM /route unavailable, using fallback: %s", exc)
        return None


async def osrm_trip(coords: List[Tuple[float, float]]) -> Optional[Dict[str, Any]]:
    """Call OSRM ``/trip`` (TSP) with fixed source + destination."""
    params = {
        "source": "first",
        "destination": "last",
        "roundtrip": "false",
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
    }
    url = f"{settings.osrm_base_url}/trip/v1/driving/{_osrm_coord_str(coords)}"
    try:
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT_S) as client:
            r = await client.get(url, params=params)
            return r.json() if r.status_code == 200 else None
    except Exception as exc:
        logger.info("OSRM /trip unavailable, using fallback: %s", exc)
        return None


def fallback_route(
    ordered_points: List[Tuple[float, float]],
    *,
    avoid_cbd: bool = False,
    eco: bool = False,
) -> Dict[str, Any]:
    """Build an OSRM-shaped response by connecting ``ordered_points`` linearly.

    When ``avoid_cbd`` is set, segments whose midpoint falls inside the CBD
    bounding box are routed via a detour outside the box.
    """
    geometry: List[List[float]] = []
    total_distance_m = 0.0

    for i in range(len(ordered_points) - 1):
        a, b = ordered_points[i], ordered_points[i + 1]
        midpoint = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if avoid_cbd and in_cbd(*midpoint):
            detour = (CBD_BBOX["max_lat"] + 0.01, CBD_BBOX["max_lng"] + 0.01)
            geometry.extend(interpolate(a, detour, 10) + interpolate(detour, b, 10))
            total_distance_m += haversine(a, detour) + haversine(detour, b)
        else:
            geometry.extend(interpolate(a, b, 12))
            total_distance_m += haversine(a, b)
    geometry.append(list(ordered_points[-1]))

    speed_mps = URBAN_SPEED_MPS_ECO if eco else URBAN_SPEED_MPS_DEFAULT
    return {
        "routes": [{
            "distance": total_distance_m,
            "duration": total_distance_m / speed_mps,
            "geometry": {"coordinates": [[p[1], p[0]] for p in geometry]},
        }]
    }


def nearest_neighbor_order(
    origin: Tuple[float, float],
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Greedy nearest-neighbour TSP heuristic over (lat, lng) items."""
    remaining = items.copy()
    current = origin
    ordered: List[Dict[str, Any]] = []
    while remaining:
        remaining.sort(key=lambda o: haversine(current, (o["lat"], o["lng"])))
        chosen = remaining.pop(0)
        ordered.append(chosen)
        current = (chosen["lat"], chosen["lng"])
    return ordered
