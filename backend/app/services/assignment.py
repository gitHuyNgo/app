"""Automatic assignment of clusters to drivers (FR-15)."""
from __future__ import annotations

from typing import Any, Dict, List, Set

from app.database import db
from app.services.geo import haversine
from app.services.hubs import get_active_hub
from app.utils import find_list, find_one


async def assign_clusters_to_drivers() -> Dict[str, Any]:
    """Distribute clusters with pending orders to the closest available driver.

    Distance is measured against each driver's zone centre when available,
    otherwise against the active hub.
    """
    clusters = await find_list("clusters")
    pending_clusters: List[Dict[str, Any]] = []
    for cluster in clusters:
        still_pending = await find_list(
            "orders",
            {"id": {"$in": cluster["order_ids"]}, "status": "pending"},
        )
        if still_pending:
            pending_clusters.append({"cluster": cluster, "orders": still_pending})

    drivers = await find_list("drivers", {"status": "available"})
    drivers.sort(key=lambda d: (d.get("vehicle_id") is None, d.get("name", "")))
    hub = await get_active_hub()

    assignments: List[Dict[str, Any]] = []
    used_drivers: Set[str] = set()

    for pending in pending_clusters:
        cluster = pending["cluster"]
        best, best_distance = None, float("inf")

        for driver in drivers:
            if driver["id"] in used_drivers:
                continue
            zone = await find_one("zones", {"id": driver["zone_id"]}) if driver.get("zone_id") else None
            reference = (
                (zone["center"][0], zone["center"][1])
                if zone
                else (hub["lat"], hub["lng"])
            )
            distance = haversine(reference, (cluster["centroid"][0], cluster["centroid"][1]))
            if distance < best_distance:
                best_distance, best = distance, driver

        if not best:
            continue

        used_drivers.add(best["id"])
        await db.orders.update_many(
            {"id": {"$in": cluster["order_ids"]}},
            {"$set": {"driver_id": best["id"], "status": "assigned"}},
        )
        assignments.append({
            "cluster_id": cluster["id"],
            "cluster_label": cluster["label"],
            "driver_id": best["id"],
            "driver_name": best["name"],
            "order_count": len(cluster["order_ids"]),
            "distance_to_cluster_m": round(best_distance),
        })

    return {"assignments": assignments, "count": len(assignments)}
