"""
Runtime configuration for the WeatherWise API.

Reads environment variables from ``.env`` and exposes a frozen ``Settings``
dataclass via the ``get_settings()`` factory.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

__all__ = ["Settings", "get_settings"]


@dataclass(frozen=True)
class Settings:
    hf_api_key: str | None
    cache_ttl_seconds: int
    request_timeout_seconds: int


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


def get_settings() -> Settings:
    return Settings(
        hf_api_key=os.getenv("HF_API_KEY"),
        cache_ttl_seconds=_read_int("WEATHERWISE_CACHE_TTL_SECONDS", 600),
        request_timeout_seconds=_read_int("WEATHERWISE_REQUEST_TIMEOUT_SECONDS", 5),
    )
