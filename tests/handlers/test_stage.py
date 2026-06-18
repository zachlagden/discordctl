from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import stage as stage_ops
from discordctl.ops.registry import BusContext


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


def make_instance(iid=7, topic="live"):
    return SimpleNamespace(
        id=iid,
        guild=SimpleNamespace(id=1),
        channel_id=200,
        topic=topic,
        privacy_level=SimpleNamespace(name="guild_only"),
        edit=AsyncMock(),
        delete=AsyncMock(),
    )


def make_channel(instance=None):
    channel = SimpleNamespace(
        id=200,
        name="stage",
        type=SimpleNamespace(name="stage_voice"),
        instance=instance,
        create_instance=AsyncMock(),
        fetch_instance=AsyncMock(),
    )
    return channel


def guild_with(channel):
    return SimpleNamespace(
        id=1, channels=[channel], get_channel=lambda cid: channel if cid == 200 else None
    )


async def test_stage_create_dry_run():
    channel = make_channel()
    guild = guild_with(channel)
    result = await stage_ops.create(
        ctx_for(guild, True), {"channel_id": 200, "topic": "live"}
    )
    assert result["planned"] is True
    channel.create_instance.assert_not_called()


async def test_stage_create_live():
    channel = make_channel()
    channel.create_instance.return_value = make_instance()
    guild = guild_with(channel)
    result = await stage_ops.create(
        ctx_for(guild, False), {"channel_id": 200, "topic": "live"}
    )
    channel.create_instance.assert_awaited_once()
    assert result["topic"] == "live"
    assert result["privacy_level"] == "guild_only"


async def test_stage_info_from_cache():
    channel = make_channel(instance=make_instance(topic="hi"))
    guild = guild_with(channel)
    result = await stage_ops.info(ctx_for(guild, True), {"channel_id": 200})
    assert result["topic"] == "hi"
    channel.fetch_instance.assert_not_called()


async def test_stage_info_fetches():
    channel = make_channel()
    channel.fetch_instance.return_value = make_instance(topic="fetched")
    guild = guild_with(channel)
    result = await stage_ops.info(ctx_for(guild, True), {"channel_id": 200})
    assert result["topic"] == "fetched"
    channel.fetch_instance.assert_awaited_once()


async def test_stage_edit_live():
    instance = make_instance()
    channel = make_channel(instance=instance)
    guild = guild_with(channel)
    await stage_ops.edit(ctx_for(guild, False), {"channel_id": 200, "topic": "new"})
    instance.edit.assert_awaited_once()
    assert instance.edit.await_args.kwargs["topic"] == "new"


async def test_stage_delete_dry_then_live():
    instance = make_instance()
    channel = make_channel(instance=instance)
    guild = guild_with(channel)
    dry = await stage_ops.delete(ctx_for(guild, True), {"channel_id": 200})
    assert dry["planned"] is True
    instance.delete.assert_not_called()
    live = await stage_ops.delete(ctx_for(guild, False), {"channel_id": 200})
    assert live["deleted"] is True
    instance.delete.assert_awaited_once()
