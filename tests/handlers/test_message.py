from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discordctl.ops.handlers import message as msg_ops
from discordctl.ops.registry import BusContext, HandlerError


def make_guild():
    channel = SimpleNamespace(
        id=200,
        name="general",
        type=SimpleNamespace(name="text"),
        send=AsyncMock(
            return_value=SimpleNamespace(
                id=999,
                channel=SimpleNamespace(id=200),
                author=SimpleNamespace(id=1, name="bot"),
                content="hi",
                pinned=False,
                created_at=None,
            )
        ),
        purge=AsyncMock(return_value=[1, 2, 3]),
    )
    guild = SimpleNamespace(
        id=1, channels=[channel], get_channel=lambda cid: channel if cid == 200 else None
    )
    return guild, channel


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


async def test_send_dry_run():
    guild, channel = make_guild()
    result = await msg_ops.send(ctx_for(guild, True), {"channel_id": 200, "content": "hi"})
    assert result["planned"] is True
    channel.send.assert_not_called()


async def test_send_live():
    guild, channel = make_guild()
    await msg_ops.send(ctx_for(guild, False), {"channel_id": 200, "content": "hi"})
    channel.send.assert_awaited_once()


async def test_purge_over_100_needs_yes_really():
    guild, channel = make_guild()
    ctx = ctx_for(guild, False)
    with pytest.raises(HandlerError):
        await msg_ops.purge(ctx, {"channel_id": 200, "limit": 500})
