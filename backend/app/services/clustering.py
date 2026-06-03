"""Order clustering service (FR-13).

Groups pending orders by zone first (so a cluster never spans two zones), then
by postal-code sector, then splits each sector into clusters whose members are
within ``max_distance_m`` of a seed. Each cluster carries its total weight and
its zone id, which the assignment service uses to match drivers/vehicles.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from app.database import db
from app.models.cluster import Cluster
from app.services.geo import haversine
from app.services.zones import find_zone_for_point
from app.utils import find_list


async def _ensure_zone_id(order: Dict[str, Any], zones_cache: List[Dict[str, Any]]) -> Optional[str]:
    """Compute the zone for an order if it's missing — keeps legacy orders working."""
    if order.get("zone_id"):
        return order["zone_id"]
    return await find_zone_for_point(order["lat"], order["lng"], zones_cache)


def _dominant_zone(orders: List[Dict[str, Any]]) -> Optional[str]:
    counts = Counter(o.get("zone_id") for o in orders if o.get("zone_id"))
    if not counts:
        return None
    zone_id, _ = counts.most_common(1)[0]
    return zone_id


async def cluster_pending_orders(max_distance_m: float) -> Dict[str, Any]:
    """Re-cluster all pending orders and persist the resulting clusters."""
    await db.clusters.delete_many({})
    await db.orders.update_many({"status": "pending"}, {"$set": {"cluster_id": None}})

    pending = await find_list("orders", {"status": "pending"})
    if not pending:
        return {"clusters": [], "count": 0, "message": "No pending orders"}

    zones_cache = await find_list("zones")

    # Bucket by (zone_id, postal_sector); zone-first means clusters never span zones.
    buckets: Dict[Tuple[Optional[str], str], List[Dict[str, Any]]] = {}
    for order in pending:
        zone_id = await _ensure_zone_id(order, zones_cache)
        # Persist zone resolution so future calls are fast & consistent.
        if zone_id and order.get("zone_id") != zone_id:
            await db.orders.update_one({"id": order["id"]}, {"$set": {"zone_id": zone_id}})
            order["zone_id"] = zone_id
        sector = (order.get("postal_code") or "00")[:2]
        buckets.setdefault((zone_id, sector), []).append(order)

    output: List[Dict[str, Any]] = []
    cluster_index = 1

    for (zone_id, sector), items in buckets.items():
        remaining = items.copy()
        while remaining:
            seed = remaining.pop(0)
            group = [seed]
            outside: List[Dict[str, Any]] = []
            for candidate in remaining:
                distance = haversine(
                    (seed["lat"], seed["lng"]),
                    (candidate["lat"], candidate["lng"]),
                )
                if distance <= max_distance_m:
                    group.append(candidate)
                else:
                    outside.append(candidate)
            remaining = outside

            centroid = [
                sum(g["lat"] for g in group) / len(group),
                sum(g["lng"] for g in group) / len(group),
            ]
            total_weight = sum(g["weight_kg"] for g in group)
            cluster = Cluster(
                label=f"C{cluster_index:03d}-{sector}",
                order_ids=[g["id"] for g in group],
                centroid=centroid,
                total_weight_kg=round(total_weight, 2),
                zone_id=zone_id or _dominant_zone(group),
            )
            await db.clusters.insert_one(cluster.model_dump())
            await db.orders.update_many(
                {"id": {"$in": cluster.order_ids}},
                {"$set": {"cluster_id": cluster.id}},
            )
            output.append(cluster.model_dump())
            cluster_index += 1

    return {"clusters": output, "count": len(output)}
