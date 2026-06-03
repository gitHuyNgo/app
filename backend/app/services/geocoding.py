"""Geocoding wrapper around OpenStreetMap Nominatim (best-effort)."""
from __future__ import annotations

from typing import Any, Dict

import httpx

from app.logging import logger

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "LionCity-AI-Logistics/1.0"


async def geocode_address(query: str) -> Dict[str, Any]:
    """Return ``{"results": [...]}`` or ``{"results": [], "error": "..."}``.

    The geocoder is rate-limited and may be blocked in some environments; this
    function never raises, so the UI can simply fall back to map-drag.
    """
    try:
        async with httpx.AsyncClient(timeout=5, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(
                NOMINATIM_URL,
                params={"q": query, "format": "json", "limit": 5, "countrycodes": "sg"},
            )
            if response.status_code != 200:
                return {"results": [], "error": f"Geocoder HTTP {response.status_code}"}
            return {
                "results": [
                    {"name": item.get("display_name"), "lat": float(item["lat"]), "lng": float(item["lon"])}
                    for item in response.json()
                ]
            }
    except Exception as exc:
        logger.info("Geocode failed for %r: %s", query, exc)
        return {"results": [], "error": "Geocoder unreachable — drag the pin on the map instead."}
