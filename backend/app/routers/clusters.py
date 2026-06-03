"""Cluster read endpoint."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter

from app.utils import find_list

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("")
async def list_clusters() -> List[dict]:
    clusters = await find_list("clusters")
    for cluster in clusters:
        cluster["order_count"] = len(cluster.get("order_ids", []))
    return clusters
