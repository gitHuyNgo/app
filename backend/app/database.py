"""MongoDB client and database singleton."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongo_url)
db: AsyncIOMotorDatabase = _client[settings.db_name]


async def close_db() -> None:
    """Gracefully close the Mongo client (called from FastAPI lifespan)."""
    _client.close()
