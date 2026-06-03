"""LTA DataMall passthrough + geocoding endpoints."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Query

from app.services.geocoding import geocode_address
from app.services.lta import fetch_lta

router = APIRouter(tags=["lta"])

SPEED_BAND_DISPLAY_LIMIT = 800


@router.get("/lta/incidents")
async def lta_incidents() -> List[Dict[str, Any]]:
    return await fetch_lta("TrafficIncidents")


@router.get("/lta/speed-bands")
async def lta_speed_bands() -> List[Dict[str, Any]]:
    """Return a truncated, map-friendly subset of TrafficSpeedBands."""
    raw = await fetch_lta("v3/TrafficSpeedBands")
    bands: List[Dict[str, Any]] = []
    for row in raw[:SPEED_BAND_DISPLAY_LIMIT]:
        try:
            bands.append({
                "LinkID": row.get("LinkID"),
                "RoadName": row.get("RoadName"),
                "SpeedBand": row.get("SpeedBand"),
                "StartLat": float(row["StartLat"]),
                "StartLon": float(row["StartLon"]),
                "EndLat": float(row["EndLat"]),
                "EndLon": float(row["EndLon"]),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return bands


@router.get("/lta/erp-rates")
async def lta_erp_rates() -> List[Dict[str, Any]]:
    return await fetch_lta("ERPRates")


@router.get("/lta/taxi-availability")
async def lta_taxi_availability() -> List[Dict[str, Any]]:
    return await fetch_lta("Taxi-Availability")


@router.get("/geocode")
async def geocode(q: str = Query(..., min_length=3)) -> Dict[str, Any]:
    return await geocode_address(q)
