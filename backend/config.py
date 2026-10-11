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


MIN_ADMIN_TOKEN_LENGTH = 24


@dataclass(frozen=True)
class Settings:
    stubs: frozenset[str] = frozenset()
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    max_upload_bytes: int = 10 * 1024 * 1024
    log_level: str = "INFO"
    # Checks allowed per client per minute. 0 turns the limit off.
    rate_limit_per_minute: int = 20
    # True only behind a proxy you control: the client address is then read from X-Forwarded-For.
    trust_proxy: bool = False
    # File that consented scam reports are appended to. Empty = reporting is off.
    reports_path: str = ""
    # Token a human reviewer sends to read the stored reports. Empty = the review endpoint is off.
    admin_token: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_graph_version: str = "v21.0"


def _flag(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in ("1", "true", "yes", "on")


def get_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    admin_token = os.getenv("ADMIN_TOKEN", "").strip()
    if admin_token and len(admin_token) < MIN_ADMIN_TOKEN_LENGTH:
        raise ValueError(f"ADMIN_TOKEN must be at least {MIN_ADMIN_TOKEN_LENGTH} characters, or empty to turn review off")
    return Settings(
        rate_limit_per_minute=max(0, int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))),
        trust_proxy=_flag("TRUST_PROXY"),
        reports_path=os.getenv("REPORTS_PATH", "").strip(),
        admin_token=admin_token,
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip(),
        whatsapp_token=os.getenv("WHATSAPP_TOKEN", "").strip(),
        whatsapp_phone_id=os.getenv("WHATSAPP_PHONE_ID", "").strip(),
        whatsapp_verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip(),
        whatsapp_app_secret=os.getenv("WHATSAPP_APP_SECRET", "").strip(),
        whatsapp_graph_version=os.getenv("WHATSAPP_GRAPH_VERSION", "v21.0").strip(),
        # Default is OFF: a deployment must never serve fake verdicts by accident.
        stubs=_parse_stubs(os.getenv("USE_STUBS", "false")),
        cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        max_upload_bytes=int(float(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
