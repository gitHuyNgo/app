"""LTA DataMall client.

Paginated GETs against ``datamall2.mytransport.sg`` with graceful failure
when the network is unreachable or the key is missing.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.logging import logger

LTA_BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"
PAGE_SIZE = 500
MAX_PAGES = 10  # 5 000 rows


async def fetch_lta(path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Fetch (paginated) data from an LTA endpoint, returning ``value`` flattened."""
    if not settings.lta_account_key:
        return []

    headers = {"AccountKey": settings.lta_account_key, "accept": "application/json"}
    url = f"{LTA_BASE_URL}/{path}"
    results: List[Dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=20) as client:
        for page in range(MAX_PAGES):
            query = dict(params or {})
            query["$skip"] = page * PAGE_SIZE
            try:
                response = await client.get(url, headers=headers, params=query)
            except Exception as exc:  # pragma: no cover — network error path
                logger.warning("LTA fetch failed (%s): %s", path, exc)
                break

            if response.status_code != 200:
                logger.warning("LTA %s → HTTP %s", path, response.status_code)
                break

            page_data = response.json().get("value", [])
            if not page_data:
                break
            results.extend(page_data)
            if len(page_data) < PAGE_SIZE:
                break

    return results
