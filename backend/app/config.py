"""Runtime configuration loaded once from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

ROOT_DIR: Path = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    mongo_url: str = field(default_factory=lambda: os.environ["MONGO_URL"])
    db_name: str = field(default_factory=lambda: os.environ["DB_NAME"])
    cors_origins: List[str] = field(
        default_factory=lambda: _split_csv(os.environ.get("CORS_ORIGINS", "*"))
    )
    lta_account_key: str = field(default_factory=lambda: os.environ.get("LTA_ACCOUNT_KEY", ""))
    osrm_base_url: str = field(
        default_factory=lambda: os.environ.get("OSRM_BASE_URL", "https://router.project-osrm.org")
    )


settings = Settings()
