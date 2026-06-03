"""Hub Manager CRUD endpoints (FR-01 / FR-02)."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from app.database import db
from app.models.hub_manager import HubManager, HubManagerIn
from app.utils import find_list, find_one, unique_phone

router = APIRouter(prefix="/hub-managers", tags=["hub-managers"])


async def _resolve_hub(data: HubManagerIn) -> tuple[str | None, str | None]:
    """Resolve hub_id → (hub_id, hub_name). Validates that the hub exists."""
    if not data.hub_id:
        return None, data.hub_name
    hub = await find_one("hubs", {"id": data.hub_id})
    if not hub:
        raise HTTPException(status_code=400, detail="Selected hub does not exist")
    return hub["id"], hub.get("name")


@router.post("", response_model=HubManager)
async def create_hub_manager(data: HubManagerIn) -> HubManager:
    if not await unique_phone("hub_managers", data.phone):
        raise HTTPException(status_code=400, detail="Phone already exists")
    hub_id, hub_name = await _resolve_hub(data)
    payload = data.model_dump()
    payload["hub_id"] = hub_id
    payload["hub_name"] = hub_name
    hub_manager = HubManager(**payload)
    await db.hub_managers.insert_one(hub_manager.model_dump())
    return hub_manager


@router.get("", response_model=List[HubManager])
async def list_hub_managers() -> List[dict]:
    return await find_list("hub_managers")


@router.put("/{hm_id}", response_model=HubManager)
async def update_hub_manager(hm_id: str, data: HubManagerIn) -> dict:
    if not await unique_phone("hub_managers", data.phone, exclude_id=hm_id):
        raise HTTPException(status_code=400, detail="Phone already exists")
    hub_id, hub_name = await _resolve_hub(data)
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    updates["hub_id"] = hub_id
    updates["hub_name"] = hub_name
    res = await db.hub_managers.find_one_and_update(
        {"id": hm_id},
        {"$set": updates},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return res


@router.delete("/{hm_id}")
async def delete_hub_manager(hm_id: str) -> dict:
    await db.hub_managers.delete_one({"id": hm_id})
    return {"ok": True}
