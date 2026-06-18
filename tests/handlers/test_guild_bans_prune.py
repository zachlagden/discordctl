from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from discordctl.ops.handlers import guild as guild_ops
from discordctl.ops.handlers import member as member_ops
from discordctl.ops.registry import BusContext, HandlerError


def make_guild():
    return SimpleNamespace(
        id=1,
        name="DigiGrow",
        owner_id=5,
        roles=[],
        channels=[],
        categories=[],
        estimate_pruned_members=AsyncMock(return_value=7),
        prune_members=AsyncMock(return_value=7),
        bulk_ban=AsyncMock(
            return_value=SimpleNamespace(
                banned=[SimpleNamespace(id=10)], failed=[SimpleNamespace(id=11)]
            )
        ),
        fetch_ban=AsyncMock(),
    )


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


async def test_prune_count_read():
    guild = make_guild()
    result = await guild_ops.prune_count(ctx_for(guild, True), {"days": 14})
    guild.estimate_pruned_members.assert_awaited_once()
    assert result["estimated"] == 7
    assert result["days"] == 14


async def test_prune_dry_run_does_not_prune():
    guild = make_guild()
    result = await guild_ops.prune(ctx_for(guild, True), {"days": 7})
    assert result["planned"] is True
    guild.prune_members.assert_not_called()


async def test_prune_live_prunes():
    guild = make_guild()
    result = await guild_ops.prune(ctx_for(guild, False), {"days": 7, "role_ids": ["3"]})
    guild.prune_members.assert_awaited_once()
    assert result["pruned"] == 7


async def test_bans_list_read():
    guild = make_guild()
    entries = [
        SimpleNamespace(
            user=SimpleNamespace(id=10, name="a", global_name=None, bot=False), reason="x"
        )
    ]

    async def gen(limit):
        for e in entries:
            yield e

    guild.bans = gen
    result = await member_ops.bans_list(ctx_for(guild, True), {})
    assert result[0]["user_id"] == "10"
    assert result[0]["reason"] == "x"


async def test_ban_info_read():
    guild = make_guild()
    guild.fetch_ban = AsyncMock(
        return_value=SimpleNamespace(
            user=SimpleNamespace(id=10, name="a", global_name=None, bot=False), reason="spam"
        )
    )
    result = await member_ops.ban_info(ctx_for(guild, True), {"user_id": 10})
    guild.fetch_ban.assert_awaited_once()
    assert result["reason"] == "spam"


async def test_ban_info_not_found():
    guild = make_guild()
    guild.fetch_ban = AsyncMock(side_effect=discord.NotFound.__new__(discord.NotFound))
    with pytest.raises(HandlerError):
        await member_ops.ban_info(ctx_for(guild, True), {"user_id": 10})


async def test_bulk_ban_dry_run_does_not_ban():
    guild = make_guild()
    result = await member_ops.bulk_ban(ctx_for(guild, True), {"user_ids": [10, 11]})
    assert result["planned"] is True
    guild.bulk_ban.assert_not_called()


async def test_bulk_ban_live_bans():
    guild = make_guild()
    result = await member_ops.bulk_ban(ctx_for(guild, False), {"user_ids": [10, 11]})
    guild.bulk_ban.assert_awaited_once()
    assert result["banned"] == ["10"]
    assert result["failed"] == ["11"]


async def test_bulk_ban_rejects_empty():
    guild = make_guild()
    with pytest.raises(HandlerError):
        await member_ops.bulk_ban(ctx_for(guild, False), {"user_ids": []})


async def test_bulk_ban_refuses_owner():
    guild = make_guild()
    with pytest.raises(HandlerError):
        await member_ops.bulk_ban(ctx_for(guild, False), {"user_ids": [5]})
