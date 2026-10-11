"""Backend settings, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

STUBBABLE = ("extract", "knowledge", "voice")


def _parse_stubs(value: str) -> frozenset[str]:
    """USE_STUBS is true/false, or a comma list of modules to stub."""
    value = value.strip().lower()
    if value in ("", "0", "false", "no", "off"):
        return frozenset()
    if value in ("1", "true", "yes", "on", "all"):
        return frozenset(STUBBABLE)
    names = frozenset(v.strip() for v in value.split(",") if v.strip())
    unknown = names - set(STUBBABLE)
    if unknown:
        raise ValueError(
            f"USE_STUBS has unknown module(s) {sorted(unknown)}; "
            f"use true, false or a comma list of {', '.join(STUBBABLE)}"
        )
    return names


@dataclass(frozen=True)
class Settings:
    stubs: frozenset[str] = frozenset()
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    max_upload_bytes: int = 10 * 1024 * 1024
    log_level: str = "INFO"


def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return Settings(
        # Default is OFF: a deployment must never serve fake verdicts by accident.
        stubs=_parse_stubs(os.getenv("USE_STUBS", "false")),
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        max_upload_bytes=int(float(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
