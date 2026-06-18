from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    discord_token: str
    bus_host: str
    bus_port: int
    bus_token: str
    write_enabled: bool
    allowed_guild_ids: frozenset[int]
    default_guild_id: int | None
    log_level: str
    sentry_dsn: str | None
    audit_path: str

    @classmethod
    def from_env(cls) -> "Config":
        discord_token = os.getenv("DISCORD_TOKEN")
        if not discord_token:
            raise RuntimeError("DISCORD_TOKEN is not set")
        bus_token = os.getenv("BUS_TOKEN")
        if not bus_token:
            raise RuntimeError("BUS_TOKEN is not set")
        return cls(
            discord_token=discord_token.strip(),
            bus_host=os.getenv("BUS_HOST", "127.0.0.1"),
            bus_port=int(os.getenv("BUS_PORT", "8765")),
            bus_token=bus_token.strip(),
            write_enabled=_as_bool(os.getenv("WRITE_ENABLED", "true")),
            allowed_guild_ids=_as_id_set(os.getenv("ALLOWED_GUILD_IDS")),
            default_guild_id=_as_int_or_none(os.getenv("DEFAULT_GUILD_ID")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            sentry_dsn=_nonempty(os.getenv("SENTRY_DSN")),
            audit_path=os.getenv("AUDIT_PATH", "./audit.jsonl"),
        )


def _as_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def _as_id_set(value: str | None) -> frozenset[int]:
    if not value or not value.strip():
        return frozenset()
    return frozenset(int(p) for p in value.split(",") if p.strip())


def _as_int_or_none(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    return int(value)


def _nonempty(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()
