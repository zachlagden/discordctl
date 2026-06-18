from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discordctl.ops.handlers import member as member_ops
from discordctl.ops.registry import BusContext, HandlerError


def make_guild(owner_id=1):
    member = SimpleNamespace(
        id=100,
        name="alice",
        display_name="alice",
        nick=None,
        bot=False,
        roles=[],
        joined_at=None,
        ban=AsyncMock(),
        kick=AsyncMock(),
    )
    guild = SimpleNamespace(
        id=1,
        owner_id=owner_id,
        members=[member],
        get_member=lambda uid: member if uid == 100 else None,
        ban=AsyncMock(),
        kick=AsyncMock(),
        unban=AsyncMock(),
    )
    return guild, member


def ctx_for(guild, dry_run):
    return BusContext(
        bot=SimpleNamespace(get_guild=lambda gid: guild),
        dry_run=dry_run,
        confirm=not dry_run,
        yes_really=False,
        actor="t",
        write_enabled=True,
        allowed_guild_ids=frozenset({1}),
        default_guild_id=1,
    )


async def test_ban_dry_run_does_not_call(monkeypatch):
    guild, member = make_guild()
    ctx = ctx_for(guild, dry_run=True)
    result = await member_ops.ban(ctx, {"user_id": 100})
    assert result["planned"] is True
    guild.ban.assert_not_called()


async def test_ban_live_calls_guild_ban():
    guild, member = make_guild()
    ctx = ctx_for(guild, dry_run=False)
    await member_ops.ban(ctx, {"user_id": 100})
    guild.ban.assert_awaited_once()


async def test_ban_refuses_owner():
    guild, member = make_guild(owner_id=100)
    ctx = ctx_for(guild, dry_run=False)
    with pytest.raises(HandlerError):
        await member_ops.ban(ctx, {"user_id": 100})
