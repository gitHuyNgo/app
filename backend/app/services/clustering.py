"""Order clustering service (FR-13) — zone & hub based.

Logic (per the LionCity ops spec):
  1. For every pending order, find the zone(s) that geographically contain its
     (lat, lng) via point-in-polygon.
  2. For each containing zone, identify the hubs that physically sit inside
     that zone polygon.
  3. If the order lies in a single zone, pick the hub IN that zone that is
     closest to the order (tie-broken by Haversine distance).
  4. If the order lies in multiple zones, evaluate the min-distance hub in
     each candidate zone and pick the overall (zone, hub) pair with the
     smallest order→hub distance — that decides both the order's zone and hub.
  5. Group all orders sharing the same (zone, hub) into one cluster.

The resulting cluster carries ``zone_id`` and ``hub_id`` so the downstream
assignment service can route it to the right driver and the route-planner can
use the cluster's hub as the journey origin (no manual hub selection needed).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.database import db
from app.models.cluster import Cluster
from app.services.geo import haversine, point_in_polygon
from app.utils import find_list


def _hubs_inside_zone(zone: Dict[str, Any], hubs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [h for h in hubs if point_in_polygon((h["lat"], h["lng"]), zone["polygon"])]


def _pick_closest_hub(
    point: Tuple[float, float],
    hubs: List[Dict[str, Any]],
) -> Optional[Tuple[Dict[str, Any], float]]:
    if not hubs:
        return None
    best = min(hubs, key=lambda h: haversine(point, (h["lat"], h["lng"])))
    return best, haversine(point, (best["lat"], best["lng"]))


async def cluster_pending_orders(_max_distance_m: float | None = None) -> Dict[str, Any]:
    """Re-cluster all pending orders into (zone, hub) buckets.

    Preserves clusters that already contain in-flight (non-pending) orders so
    the route planner can keep resolving their hub.
    """
    # Preserve any cluster that has at least one non-pending order in it.
    all_orders = await find_list("orders")
    orders_by_id = {o["id"]: o for o in all_orders}
    existing_clusters = await find_list("clusters")
    keep_ids: List[str] = []
    for c in existing_clusters:
        if any(
            orders_by_id.get(oid, {}).get("status") and
            orders_by_id[oid]["status"] != "pending"
            for oid in c.get("order_ids", [])
        ):
            keep_ids.append(c["id"])
    await db.clusters.delete_many({"id": {"$nin": keep_ids}})
    await db.orders.update_many({"status": "pending"}, {"$set": {"cluster_id": None}})

    pending = await find_list("orders", {"status": "pending"})
    if not pending:
        return {"clusters": [], "count": 0, "message": "No pending orders", "unassigned": 0}

    zones = await find_list("zones")
    hubs = await find_list("hubs")

    if not zones:
        return {"clusters": [], "count": 0, "message": "No zones defined", "unassigned": len(pending)}
    if not hubs:
        return {"clusters": [], "count": 0, "message": "No hubs defined", "unassigned": len(pending)}

    # Pre-compute hubs inside each zone polygon.
    zone_hubs: Dict[str, List[Dict[str, Any]]] = {
        z["id"]: _hubs_inside_zone(z, hubs) for z in zones
    }

    # Bucket: (zone_id, hub_id) → list of orders.
    buckets: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    bucket_meta: Dict[Tuple[str, str], Tuple[Dict[str, Any], Dict[str, Any]]] = {}
    unassigned: List[str] = []

    for order in pending:
        point = (order["lat"], order["lng"])

        # Step 1: every zone that contains the order.
        matching_zones = [z for z in zones if point_in_polygon(point, z["polygon"])]
        if not matching_zones:
            unassigned.append(order["id"])
            continue

        # Step 2 + 3 + 4: pick the best (zone, hub) pair by min order→hub distance.
        zone_hub_candidates: List[Tuple[Dict[str, Any], Dict[str, Any], float]] = []
        for zone in matching_zones:
            in_zone_hubs = zone_hubs.get(zone["id"], [])
            if in_zone_hubs:
                hub, dist = _pick_closest_hub(point, in_zone_hubs)
            else:
                # Zone has no hub inside it → fall back to nearest hub overall.
                picked = _pick_closest_hub(point, hubs)
                if picked is None:
                    continue
                hub, dist = picked
            zone_hub_candidates.append((zone, hub, dist))

        if not zone_hub_candidates:
            unassigned.append(order["id"])
            continue

        zone_hub_candidates.sort(key=lambda x: x[2])
        chosen_zone, chosen_hub, _ = zone_hub_candidates[0]

        # Persist the resolved zone_id on the order document.
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {"zone_id": chosen_zone["id"]}},
        )
        order["zone_id"] = chosen_zone["id"]

        key = (chosen_zone["id"], chosen_hub["id"])
        buckets.setdefault(key, []).append(order)
        bucket_meta.setdefault(key, (chosen_zone, chosen_hub))

    # Step 5: materialise one Cluster per (zone, hub) bucket.
    output: List[Dict[str, Any]] = []
    for index, (key, items) in enumerate(buckets.items(), start=1):
        zone, hub = bucket_meta[key]
        centroid = [
            sum(o["lat"] for o in items) / len(items),
            sum(o["lng"] for o in items) / len(items),
        ]
        cluster = Cluster(
            label=f"C{index:03d} · {zone['name']} / {hub['name']}",
            order_ids=[o["id"] for o in items],
            centroid=centroid,
            total_weight_kg=round(sum(o["weight_kg"] for o in items), 2),
            zone_id=zone["id"],
            zone_name=zone["name"],
            hub_id=hub["id"],
            hub_name=hub["name"],
        )
        await db.clusters.insert_one(cluster.model_dump())
        await db.orders.update_many(
            {"id": {"$in": cluster.order_ids}},
            {"$set": {"cluster_id": cluster.id}},
        )
        output.append(cluster.model_dump())

    return {
        "clusters": output,
        "count": len(output),
        "unassigned": len(unassigned),
        "unassigned_order_ids": unassigned,
    }
