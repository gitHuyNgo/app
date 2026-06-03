"""Hub CRUD endpoints (multi-location depots)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from app.database import db
from app.models.hub import Hub, HubIn
from app.utils import find_list, find_one

router = APIRouter(prefix="/hubs", tags=["hubs"])


@router.post("", response_model=Hub)
async def create_hub(data: HubIn) -> Hub:
    hub = Hub(**data.model_dump())
    if hub.is_default:
        await db.hubs.update_many({}, {"$set": {"is_default": False}})
    await db.hubs.insert_one(hub.model_dump())
    if not await db.hubs.find_one({"is_default": True}, {"_id": 0}):
        await db.hubs.update_one({"id": hub.id}, {"$set": {"is_default": True}})
        hub.is_default = True
    return hub


@router.get("", response_model=List[Hub])
async def list_hubs() -> List[dict]:
    return await find_list("hubs")


@router.put("/{hub_id}", response_model=Hub)
async def update_hub(hub_id: str, data: HubIn) -> dict:
    if data.is_default:
        await db.hubs.update_many({"id": {"$ne": hub_id}}, {"$set": {"is_default": False}})
    res = await db.hubs.find_one_and_update(
        {"id": hub_id},
        {"$set": data.model_dump()},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return res


@router.delete("/{hub_id}")
async def delete_hub(hub_id: str) -> dict:
    target = await find_one("hubs", {"id": hub_id})
    if not target:
        raise HTTPException(status_code=404, detail="Not found")
    await db.hubs.delete_one({"id": hub_id})
    # Promote another hub to default if we just removed the default one.
    if target.get("is_default"):
        any_hub = await db.hubs.find_one({}, {"_id": 0})
        if any_hub:
            await db.hubs.update_one({"id": any_hub["id"]}, {"$set": {"is_default": True}})
    return {"ok": True}
