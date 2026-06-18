from types import SimpleNamespace
from unittest.mock import AsyncMock

from claude_control.ops.handlers import channel as channel_ops
from claude_control.ops.registry import BusContext


def make_guild():
    ch = SimpleNamespace(
        id=200, name="general", position=0,
        type=SimpleNamespace(name="text"), category_id=None, topic=None,
        nsfw=False, slowmode_delay=0,
        edit=AsyncMock(), delete=AsyncMock(), clone=AsyncMock(),
    )
    guild = SimpleNamespace(
        id=1, channels=[ch], text_channels=[ch],
        get_channel=lambda cid: ch if cid == 200 else None,
        create_text_channel=AsyncMock(return_value=ch),
    )
    return guild, ch


def ctx_for(guild, dry_run):
    return BusContext(bot=SimpleNamespace(get_guild=lambda gid: guild),
                      dry_run=dry_run, confirm=not dry_run, yes_really=False, actor="t",
                      write_enabled=True, allowed_guild_ids=frozenset({1}), default_guild_id=1)


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


async def test_edit_live_filters_fields():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=False)
    await channel_ops.edit(ctx, {"channel_id": 200, "topic": "hi"})
    ch.edit.assert_awaited_once()
