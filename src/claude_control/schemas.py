from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    op: str = Field(description="Dotted op name, e.g. guild.info")
    args: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = Field(default=True)
    confirm: bool = Field(default=False)
    yes_really: bool = Field(default=False)


class OpResponse(BaseModel):
    ok: bool
    data: Any = None
    error: Any = None
    request_id: str | None = None
    dry_run: bool | None = None
    must_confirm: bool | None = None
