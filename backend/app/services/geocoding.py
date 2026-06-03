"""Geocoding wrappers.

Primary provider: OneMap.gov.sg — Singapore's official mapping service.
  • search:  public endpoint, no auth, no rate limit
  • reverse: requires a Bearer token (free OneMap account → /api/auth/post/getToken).
            We use it when ``ONEMAP_TOKEN`` is configured, otherwise we fall
            back to Nominatim (rate-limited but free, no signup).

Either way every call is wrapped in a try/except: the UI gracefully falls
back to drag-the-pin when nothing works.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx

from app.logging import logger

# OneMap endpoints
ONEMAP_SEARCH = "https://www.onemap.gov.sg/api/common/elastic/search"
ONEMAP_REVERSE = "https://www.onemap.gov.sg/api/public/revgeocode"

# Nominatim fallback (reverse only)
NOMINATIM_REVERSE = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "LionCity-AI-Logistics/1.0"


def _onemap_token() -> str:
    return os.environ.get("ONEMAP_TOKEN", "")


def _onemap_result(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a OneMap /search row into our common shape (raises on bad row)."""
    return {
        "name": row.get("ADDRESS") or row.get("SEARCHVAL"),
        "lat": float(row["LATITUDE"]),
        "lng": float(row["LONGITUDE"]),
        "postal_code": (row.get("POSTAL") or "").replace("NIL", "").strip(),
    }


async def geocode_address(query: str) -> Dict[str, Any]:
    """Address → list of candidate locations (Singapore-only, via OneMap)."""
    try:
        async with httpx.AsyncClient(timeout=6, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(
                ONEMAP_SEARCH,
                params={
                    "searchVal": query,
                    "returnGeom": "Y",
                    "getAddrDetails": "Y",
                    "pageNum": 1,
                },
            )
            if response.status_code != 200:
                return {"results": [], "error": f"OneMap HTTP {response.status_code}"}
            data = response.json()
            rows: List[Dict[str, Any]] = data.get("results") or []
            normalised: List[Dict[str, Any]] = []
            for row in rows[:8]:
                try:
                    normalised.append(_onemap_result(row))
                except (KeyError, TypeError, ValueError) as row_exc:
                    logger.debug("Skipping OneMap row (%s): %r", row_exc, row.get("SEARCHVAL"))
                    continue
            return {"results": normalised}
    except Exception as exc:
        logger.info("OneMap search failed for %r: %s", query, exc, exc_info=True)
        return {"results": [], "error": "Geocoder unreachable — drag the pin on the map instead."}


async def _reverse_onemap(lat: float, lng: float) -> Dict[str, Any]:
    """OneMap reverse geocode — requires a Bearer token."""
    token = _onemap_token()
    if not token:
        return {}
    headers = {"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=6, headers=headers) as client:
        response = await client.get(
            ONEMAP_REVERSE,
            params={"location": f"{lat},{lng}", "buffer": 50, "addressType": "All"},
        )
        if response.status_code != 200:
            return {}
        data = response.json()
        rows = data.get("GeocodeInfo") or []
        if not rows:
            return {}
        row = rows[0]
        parts = [row.get("BLOCK"), row.get("ROAD"), row.get("BUILDINGNAME"), f"Singapore {row.get('POSTALCODE', '')}"]
        name = " ".join([p for p in parts if p])
        return {
            "name": name.strip(),
            "lat": float(row.get("LATITUDE", lat)),
            "lng": float(row.get("LONGITUDE", lng)),
            "postal_code": row.get("POSTALCODE", ""),
            "provider": "onemap",
        }


async def _reverse_nominatim(lat: float, lng: float) -> Dict[str, Any]:
    """Nominatim fallback when OneMap token is not configured."""
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=6, headers=headers) as client:
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
            "provider": "nominatim",
        }


async def reverse_geocode(lat: float, lng: float) -> Dict[str, Any]:
    """(lat, lng) → address. Prefers OneMap when token is set, else Nominatim."""
    try:
        if _onemap_token():
            result = await _reverse_onemap(lat, lng)
            if result:
                return result
        return await _reverse_nominatim(lat, lng)
    except Exception as exc:
        logger.info("Reverse geocode failed for (%s, %s): %s", lat, lng, exc)
        return {"name": None, "postal_code": "", "error": "Reverse geocoder unreachable."}
