from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discordctl.ops.handlers import channel as channel_ops
from discordctl.ops.registry import BusContext, HandlerError


def make_guild():
    ch = SimpleNamespace(
        id=200,
        name="general",
        position=0,
        type=SimpleNamespace(name="text"),
        category_id=None,
        topic=None,
        nsfw=False,
        slowmode_delay=0,
        edit=AsyncMock(),
        delete=AsyncMock(),
        clone=AsyncMock(),
    )
    guild = SimpleNamespace(
        id=1,
        channels=[ch],
        text_channels=[ch],
        get_channel=lambda cid: ch if cid == 200 else None,
        create_text_channel=AsyncMock(return_value=ch),
        create_category=AsyncMock(return_value=ch),
    )
    return guild, ch


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


async def test_create_dry_run():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=True)
    result = await channel_ops.create(ctx, {"name": "new", "type": "text"})
    assert result["planned"] is True
    guild.create_text_channel.assert_not_called()


async def test_create_live():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=False)
    await channel_ops.create(ctx, {"name": "new", "type": "text"})
    guild.create_text_channel.assert_awaited_once()


async def test_create_category_rejects_topic():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=False)
    with pytest.raises(HandlerError) as exc_info:
        await channel_ops.create(ctx, {"name": "cat", "type": "category", "topic": "x"})
    assert exc_info.value.code == "bad_args"
    guild.create_category.assert_not_called()


async def test_edit_live_filters_fields():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=False)
    await channel_ops.edit(ctx, {"channel_id": 200, "topic": "hi", "color": "red"})
    ch.edit.assert_awaited_once_with(reason=None, topic="hi")


@pytest.mark.parametrize(
    "handler, args, mock_attr",
    [
        (channel_ops.delete, {"channel_id": 200}, "delete"),
        (channel_ops.move, {"channel_id": 200, "position": 3}, "edit"),
        (channel_ops.clone, {"channel_id": 200}, "clone"),
        (channel_ops.sync, {"channel_id": 200}, "edit"),
    ],
)
async def test_mutating_ops_dry_run_no_mutation(handler, args, mock_attr):
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=True)
    result = await handler(ctx, args)
    assert result["planned"] is True
    getattr(ch, mock_attr).assert_not_awaited()
