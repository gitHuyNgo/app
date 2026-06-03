"""Geocoding wrapper around OpenStreetMap Nominatim (best-effort)."""
from __future__ import annotations

from typing import Any, Dict

import httpx

from app.logging import logger

NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "LionCity-AI-Logistics/1.0"


async def geocode_address(query: str) -> Dict[str, Any]:
    """Address → list of candidate locations (with postal code when known)."""
    try:
        async with httpx.AsyncClient(timeout=5, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(
                NOMINATIM_SEARCH,
                params={
                    "q": query,
                    "format": "json",
                    "limit": 5,
                    "countrycodes": "sg",
                    "addressdetails": 1,
                },
            )
            if response.status_code != 200:
                return {"results": [], "error": f"Geocoder HTTP {response.status_code}"}
            return {
                "results": [
                    {
                        "name": item.get("display_name"),
                        "lat": float(item["lat"]),
                        "lng": float(item["lon"]),
                        "postal_code": (item.get("address") or {}).get("postcode", ""),
                    }
                    for item in response.json()
                ]
            }
    except Exception as exc:
        logger.info("Geocode failed for %r: %s", query, exc)
        return {"results": [], "error": "Geocoder unreachable — drag the pin on the map instead."}


async def reverse_geocode(lat: float, lng: float) -> Dict[str, Any]:
    """(lat, lng) → human-readable address + postal code."""
    try:
        async with httpx.AsyncClient(timeout=5, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(
                NOMINATIM_REVERSE,
                params={"lat": lat, "lon": lng, "format": "json", "addressdetails": 1, "zoom": 18},
            )
            if response.status_code != 200:
                return {"name": None, "postal_code": "", "error": f"Reverse HTTP {response.status_code}"}
            data = response.json()
            return {
                "name": data.get("display_name"),
                "lat": float(data["lat"]),
                "lng": float(data["lon"]),
                "postal_code": (data.get("address") or {}).get("postcode", ""),
            }
    except Exception as exc:
        logger.info("Reverse geocode failed for (%s, %s): %s", lat, lng, exc)
        return {"name": None, "postal_code": "", "error": "Reverse geocoder unreachable."}
