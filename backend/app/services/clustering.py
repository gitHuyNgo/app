"""Order clustering service (FR-13).

Groups pending orders by postal-code sector then splits each sector into
clusters whose members are within ``max_distance_m`` of a seed.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.database import db
from app.models.cluster import Cluster
from app.services.geo import haversine
from app.utils import find_list


async def cluster_pending_orders(max_distance_m: float) -> Dict[str, Any]:
    """Re-cluster all pending orders and persist the resulting clusters."""
    await db.clusters.delete_many({})
    await db.orders.update_many(
        {"status": "pending"},
        {"$set": {"cluster_id": None}},
    )

    pending = await find_list("orders", {"status": "pending"})
    if not pending:
        return {"clusters": [], "count": 0, "message": "No pending orders"}

    sectors: Dict[str, List[Dict[str, Any]]] = {}
    for order in pending:
        sector_key = (order.get("postal_code") or "00")[:2]
        sectors.setdefault(sector_key, []).append(order)

    output: List[Dict[str, Any]] = []
    cluster_index = 1
    for sector, items in sectors.items():
        remaining = items.copy()
        while remaining:
            seed = remaining.pop(0)
            group = [seed]
            outside_radius: List[Dict[str, Any]] = []
            for candidate in remaining:
                distance = haversine(
                    (seed["lat"], seed["lng"]),
                    (candidate["lat"], candidate["lng"]),
                )
                if distance <= max_distance_m:
                    group.append(candidate)
                else:
                    outside_radius.append(candidate)
            remaining = outside_radius

            centroid = [
                sum(g["lat"] for g in group) / len(group),
                sum(g["lng"] for g in group) / len(group),
            ]
            cluster = Cluster(
                label=f"C{cluster_index:03d}-{sector}",
                order_ids=[g["id"] for g in group],
                centroid=centroid,
            )
            await db.clusters.insert_one(cluster.model_dump())
            await db.orders.update_many(
                {"id": {"$in": cluster.order_ids}},
                {"$set": {"cluster_id": cluster.id}},
            )
            output.append(cluster.model_dump())
            cluster_index += 1

    return {"clusters": output, "count": len(output)}
