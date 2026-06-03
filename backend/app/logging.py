"""Centralised logging configuration."""
from __future__ import annotations

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

logger: logging.Logger = logging.getLogger("lioncity")
