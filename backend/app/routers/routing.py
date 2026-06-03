"""Routing endpoints (FR-17, FR-18)."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, HTTPException

from app.database import db
from app.models.route import RoutePlanIn, RouteRecord, SimulateStepIn
from app.services.geo import haversine
from app.services.hubs import get_active_hub
from app.services.routing import (
    fallback_route,
    nearest_neighbor_order,
    osrm_route,
    osrm_trip,
)
from app.utils import find_list, find_one, now_iso

router = APIRouter(tags=["routing"])

CBD_REFERENCE: Tuple[float, float] = (1.2839, 103.8507)


def _route_cbd_penalty(route: Dict[str, Any]) -> float:
    """How far the route's midpoint sits from the CBD reference point."""
    geometry = route["geometry"]["coordinates"]
    midpoint = geometry[len(geometry) // 2]
    return haversine(CBD_REFERENCE, (midpoint[1], midpoint[0]))


async def _plan_eco(orders: List[Dict[str, Any]], start: Tuple[float, float]):
    ordered = nearest_neighbor_order(start, orders)
    sequence = [o["id"] for o in ordered]
    coords = [start] + [(o["lat"], o["lng"]) for o in ordered]
    route = await osrm_route(coords) or fallback_route(coords, eco=True)
    return sequence, route


async def _plan_avoid_erp(orders: List[Dict[str, Any]], start: Tuple[float, float]):
    ordered = nearest_neighbor_order(start, orders)
    sequence = [o["id"] for o in ordered]
    coords = [start] + [(o["lat"], o["lng"]) for o in ordered]
    osrm_result = await osrm_route(coords, alternatives=True)
    if osrm_result and osrm_result.get("routes"):
        # Pick the alternative whose midpoint is farthest from the CBD.
        alternatives = sorted(osrm_result["routes"], key=_route_cbd_penalty, reverse=True)
        return sequence, {"routes": [alternatives[0]]}
    return sequence, fallback_route(coords, avoid_cbd=True)


async def _plan_time(
    orders: List[Dict[str, Any]],
    start: Tuple[float, float],
    stops: List[Tuple[float, float]],
):
    trip = await osrm_trip([start] + stops)
    if trip and trip.get("trips"):
        waypoints = trip.get("waypoints", [])
        sequence_indexes = sorted(
            range(1, len(waypoints)),
            key=lambda i: waypoints[i]["waypoint_index"],
        )
        sequence = [orders[i - 1]["id"] for i in sequence_indexes]
        return sequence, {"routes": trip["trips"]}

    ordered = nearest_neighbor_order(start, orders)
    sequence = [o["id"] for o in ordered]
    coords = [start] + [(o["lat"], o["lng"]) for o in ordered]
    route = await osrm_route(coords) or fallback_route(coords)
    return sequence, route


@router.post("/routing/plan", response_model=RouteRecord)
async def plan_route(body: RoutePlanIn) -> RouteRecord:
    driver = await find_one("drivers", {"id": body.driver_id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    orders = await find_list("orders", {
        "driver_id": body.driver_id,
        "status": {"$in": ["assigned", "delivering"]},
    })
    if not orders:
        raise HTTPException(status_code=400, detail="No active orders for this driver")

    hub = await get_active_hub(body.hub_id)
    start: Tuple[float, float] = (hub["lat"], hub["lng"])
    stops: List[Tuple[float, float]] = [(o["lat"], o["lng"]) for o in orders]

    if body.mode == "eco":
        sequence_order_ids, routing_result = await _plan_eco(orders, start)
    elif body.mode == "avoid_erp":
        sequence_order_ids, routing_result = await _plan_avoid_erp(orders, start)
    else:
        sequence_order_ids, routing_result = await _plan_time(orders, start, stops)

    route_json = routing_result["routes"][0]
    # OSRM returns coordinates as [lng, lat]; Leaflet expects [lat, lng].
    geometry = [[c[1], c[0]] for c in route_json["geometry"]["coordinates"]]

    for idx, order_id in enumerate(sequence_order_ids, start=1):
        await db.orders.update_one({"id": order_id}, {"$set": {"sequence": idx}})

    record = RouteRecord(
        driver_id=body.driver_id,
        mode=body.mode,
        waypoints=[list(start)] + [[orders[i]["lat"], orders[i]["lng"]] for i in range(len(orders))],
        ordered_order_ids=sequence_order_ids,
        distance_m=route_json["distance"],
        duration_s=route_json["duration"],
        geometry=geometry,
    )
    await db.routes.delete_many({"driver_id": body.driver_id})
    await db.routes.insert_one(record.model_dump())
    return record


@router.get("/routing/{driver_id}")
async def get_route(driver_id: str) -> dict:
    record = await find_one("routes", {"driver_id": driver_id})
    if not record:
        raise HTTPException(status_code=404, detail="No route")
    return record


@router.post("/drivers/{driver_id}/simulate-step")
async def simulate_step(driver_id: str, body: SimulateStepIn) -> dict:
    """Advance a driver along their planned route — used for FR-18 demos."""
    route = await find_one("routes", {"driver_id": driver_id})
    if not route:
        raise HTTPException(status_code=404, detail="No route for driver")

    driver = await find_one("drivers", {"id": driver_id})
    geometry = route["geometry"]
    current = driver.get("location") if driver else None

    if not current:
        index = 0
    else:
        # Find the closest geometry point and walk forward by ``step_m``.
        index = min(
            range(len(geometry)),
            key=lambda i: haversine(
                (current["lat"], current["lng"]),
                (geometry[i][0], geometry[i][1]),
            ),
        )
        travelled = 0.0
        while index < len(geometry) - 1 and travelled < body.step_m:
            travelled += haversine(
                (geometry[index][0], geometry[index][1]),
                (geometry[index + 1][0], geometry[index + 1][1]),
            )
            index += 1

    new_location = {
        "lat": geometry[index][0],
        "lng": geometry[index][1],
        "updated_at": now_iso(),
    }
    await db.drivers.update_one(
        {"id": driver_id},
        {"$set": {"location": new_location, "status": "delivering"}},
    )
    progress_pct = round(100 * index / max(1, len(geometry) - 1), 1)
    return {"location": new_location, "progress_pct": progress_pct}
