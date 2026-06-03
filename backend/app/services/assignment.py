"""Automatic cluster → driver assignment with proper logistics rules (FR-15).

Constraints (hard — a driver is excluded if any fails):
  • Driver is ``available`` and has a vehicle assigned.
  • Driver's license type is compatible with the vehicle type.
  • Vehicle's capacity_kg ≥ cluster's total weight (the load must fit).

Preferences (soft — composed into a score, highest wins):
  • Zone affinity         : driver's zone == cluster's zone        (+1000)
  • Vehicle right-sizing  : prefer smallest vehicle that still fits — penalise unused
                            capacity. This prevents using an 800 kg van for 2 kg.
  • EV bonus              : prefer electric vehicles when route stays short  (+50)
  • Distance              : driver zone centre → cluster centroid (penalty per km)

Heavier clusters are matched first so they don't get stranded with motorbikes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from app.database import db
from app.services.geo import haversine
from app.services.hubs import get_active_hub
from app.utils import find_list, find_one

# License → vehicle-type compatibility.
LICENSE_VEHICLE_MATRIX: Dict[str, Set[str]] = {
    "A": {"motorbike"},
    "B": {"motorbike", "van"},
    "C": {"van"},
}

ZONE_MATCH_BONUS = 1000.0
EV_BONUS = 50.0
DISTANCE_PENALTY_PER_KM = 0.5
CAPACITY_WASTE_PENALTY_PER_KG = 0.4


def license_allows(license_type: str, vehicle_type: str) -> bool:
    return vehicle_type in LICENSE_VEHICLE_MATRIX.get(license_type, set())


async def _eligible_drivers_for_cluster(
    cluster: Dict[str, Any],
    drivers: List[Dict[str, Any]],
    vehicles_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Filter drivers to those whose vehicle fits the cluster (license + capacity)."""
    eligible: List[Dict[str, Any]] = []
    weight = cluster.get("total_weight_kg") or 0.0
    for driver in drivers:
        vehicle_id = driver.get("vehicle_id")
        if not vehicle_id:
            continue
        vehicle = vehicles_by_id.get(vehicle_id)
        if not vehicle:
            continue
        if not license_allows(driver.get("license_type", ""), vehicle["type"]):
            continue
        if vehicle["capacity_kg"] < weight:
            continue
        eligible.append({"driver": driver, "vehicle": vehicle})
    return eligible


async def _score_candidate(
    candidate: Dict[str, Any],
    cluster: Dict[str, Any],
    hub: Dict[str, Any],
) -> float:
    driver, vehicle = candidate["driver"], candidate["vehicle"]
    score = 0.0

    # 1. Zone affinity (huge boost when driver works in the same zone)
    if cluster.get("zone_id") and driver.get("zone_id") == cluster["zone_id"]:
        score += ZONE_MATCH_BONUS

    # 2. Right-sizing — penalise leftover capacity (waste avoidance)
    weight = cluster.get("total_weight_kg") or 0.0
    unused = max(vehicle["capacity_kg"] - weight, 0.0)
    score -= CAPACITY_WASTE_PENALTY_PER_KG * unused

    # 3. EV preference
    if vehicle.get("fuel_type") == "ev":
        score += EV_BONUS

    # 4. Distance from driver's reference (zone centre or hub) to cluster centroid
    if driver.get("zone_id"):
        zone = await find_one("zones", {"id": driver["zone_id"]})
        ref = (zone["center"][0], zone["center"][1]) if zone else (hub["lat"], hub["lng"])
    else:
        ref = (hub["lat"], hub["lng"])
    distance_km = haversine(ref, (cluster["centroid"][0], cluster["centroid"][1])) / 1000.0
    score -= DISTANCE_PENALTY_PER_KM * distance_km

    return score


async def assign_clusters_to_drivers() -> Dict[str, Any]:
    """Distribute clusters to available, compatible drivers using a scoring heuristic."""
    clusters = await find_list("clusters")
    if not clusters:
        return {"assignments": [], "count": 0, "skipped": [], "message": "No clusters — run clustering first."}

    # Keep only clusters that still have at least one pending order.
    active_clusters: List[Dict[str, Any]] = []
    for cluster in clusters:
        still_pending = await find_list(
            "orders",
            {"id": {"$in": cluster["order_ids"]}, "status": "pending"},
        )
        if still_pending:
            cluster_copy = {**cluster, "_pending_orders": still_pending}
            # Recompute current weight from still-pending orders only.
            cluster_copy["total_weight_kg"] = round(sum(o["weight_kg"] for o in still_pending), 2)
            active_clusters.append(cluster_copy)

    if not active_clusters:
        return {"assignments": [], "count": 0, "skipped": [], "message": "No pending orders."}

    drivers = await find_list("drivers", {"status": "available"})
    vehicles = await find_list("vehicles")
    vehicles_by_id = {v["id"]: v for v in vehicles}
    hub = await get_active_hub()

    # Heaviest clusters first so they aren't stuck with motorbike-only drivers later.
    active_clusters.sort(key=lambda c: c.get("total_weight_kg", 0), reverse=True)

    assignments: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    used_drivers: Set[str] = set()

    for cluster in active_clusters:
        candidates = await _eligible_drivers_for_cluster(cluster, drivers, vehicles_by_id)
        candidates = [c for c in candidates if c["driver"]["id"] not in used_drivers]
        if not candidates:
            skipped.append({
                "cluster_id": cluster["id"],
                "cluster_label": cluster["label"],
                "reason": "No eligible driver — check capacity / license / availability.",
                "total_weight_kg": cluster.get("total_weight_kg"),
            })
            continue

        # Score and pick the best fit.
        scored = []
        for candidate in candidates:
            score = await _score_candidate(candidate, cluster, hub)
            scored.append((score, candidate))
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best = scored[0]
        driver, vehicle = best["driver"], best["vehicle"]
        used_drivers.add(driver["id"])

        await db.orders.update_many(
            {"id": {"$in": cluster["order_ids"]}, "status": "pending"},
            {"$set": {"driver_id": driver["id"], "status": "assigned"}},
        )

        assignments.append({
            "cluster_id": cluster["id"],
            "cluster_label": cluster["label"],
            "driver_id": driver["id"],
            "driver_name": driver["name"],
            "vehicle_id": vehicle["id"],
            "vehicle_plate": vehicle["plate"],
            "vehicle_type": vehicle["type"],
            "vehicle_fuel": vehicle["fuel_type"],
            "vehicle_capacity_kg": vehicle["capacity_kg"],
            "cluster_weight_kg": cluster.get("total_weight_kg"),
            "utilisation_pct": round(
                100.0 * (cluster.get("total_weight_kg") or 0.0) / max(vehicle["capacity_kg"], 1e-6),
                1,
            ),
            "zone_match": bool(cluster.get("zone_id") and driver.get("zone_id") == cluster["zone_id"]),
            "score": round(best_score, 1),
            "order_count": len(cluster["order_ids"]),
        })

    return {
        "assignments": assignments,
        "count": len(assignments),
        "skipped": skipped,
    }
