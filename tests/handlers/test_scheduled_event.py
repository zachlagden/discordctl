from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import discord

from discordctl.ops.handlers import scheduled_event as event_ops
from discordctl.ops.registry import BusContext, HandlerError


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


def fake_event(eid=10):
    return SimpleNamespace(
        id=eid,
        guild_id=1,
        name="launch",
        description="desc",
        entity_type=discord.EntityType.external,
        status=discord.EventStatus.scheduled,
        privacy_level=discord.PrivacyLevel.guild_only,
        start_time=None,
        end_time=None,
        channel_id=None,
        creator_id=None,
        user_count=0,
        location="space",
        edit=AsyncMock(),
        delete=AsyncMock(),
    )


def guild_with(event=None, create_event=None):
    async def fetch(eid):
        if event is None:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "x")
        return event

    return SimpleNamespace(
        id=1,
        scheduled_events=[event] if event else [],
        get_scheduled_event=lambda eid: event if event and eid == event.id else None,
        fetch_scheduled_event=fetch,
        create_scheduled_event=create_event or AsyncMock(),
    )


async def test_event_list():
    guild = guild_with(fake_event())
    result = await event_ops.list_events(ctx_for(guild, True), {})
    assert result[0]["name"] == "launch"
    assert result[0]["entity_type"] == "external"
    assert result[0]["status"] == "scheduled"
    assert result[0]["privacy_level"] == "guild_only"


async def test_event_create_dry_run():
    guild = guild_with()
    args = {
        "name": "launch",
        "start_time": "2026-07-01T10:00:00",
        "end_time": "2026-07-01T12:00:00",
        "entity_type": "external",
        "location": "space",
    }
    result = await event_ops.create(ctx_for(guild, True), args)
    assert result["planned"] is True
    guild.create_scheduled_event.assert_not_called()


async def test_event_create_live():
    created = fake_event()
    guild = guild_with(create_event=AsyncMock(return_value=created))
    args = {
        "name": "launch",
        "start_time": "2026-07-01T10:00:00",
        "end_time": "2026-07-01T12:00:00",
        "entity_type": "external",
        "location": "space",
    }
    result = await event_ops.create(ctx_for(guild, False), args)
    assert result["name"] == "launch"
    guild.create_scheduled_event.assert_awaited_once()
    kwargs = guild.create_scheduled_event.await_args.kwargs
    assert kwargs["entity_type"] == discord.EntityType.external
    assert kwargs["location"] == "space"


async def test_event_create_voice_live_uses_channel():
    created = fake_event()
    guild = guild_with(create_event=AsyncMock(return_value=created))
    args = {
        "name": "talk",
        "start_time": "2026-07-01T10:00:00",
        "entity_type": "voice",
        "channel_id": 555,
    }
    await event_ops.create(ctx_for(guild, False), args)
    kwargs = guild.create_scheduled_event.await_args.kwargs
    assert int(kwargs["channel"].id) == 555


async def test_event_create_bad_entity_type():
    guild = guild_with()
    args = {"name": "x", "start_time": "2026-07-01T10:00:00", "entity_type": "nope"}
    with pytest.raises(HandlerError) as exc:
        await event_ops.create(ctx_for(guild, True), args)
    assert exc.value.code == "bad_args"


async def test_event_create_external_missing_location():
    guild = guild_with()
    args = {
        "name": "x",
        "start_time": "2026-07-01T10:00:00",
        "end_time": "2026-07-01T12:00:00",
        "entity_type": "external",
    }
    with pytest.raises(HandlerError) as exc:
        await event_ops.create(ctx_for(guild, True), args)
    assert exc.value.code == "bad_args"


async def test_event_edit_dry_run():
    event = fake_event()
    guild = guild_with(event)
    result = await event_ops.edit(ctx_for(guild, True), {"event_id": 10, "name": "new"})
    assert result["planned"] is True
    event.edit.assert_not_called()


async def test_event_edit_live():
    event = fake_event()
    guild = guild_with(event)
    args = {"event_id": 10, "name": "new", "status": "active", "start_time": "2026-07-01T10:00:00"}
    await event_ops.edit(ctx_for(guild, False), args)
    event.edit.assert_awaited_once()
    kwargs = event.edit.await_args.kwargs
    assert kwargs["name"] == "new"
    assert kwargs["status"] == discord.EventStatus.active


async def test_event_delete_dry_run():
    event = fake_event()
    guild = guild_with(event)
    result = await event_ops.delete(ctx_for(guild, True), {"event_id": 10})
    assert result["planned"] is True
    event.delete.assert_not_called()


async def test_event_delete_live():
    event = fake_event()
    guild = guild_with(event)
    result = await event_ops.delete(ctx_for(guild, False), {"event_id": 10})
    assert result["deleted"] is True
    event.delete.assert_awaited_once()


async def test_event_users():
    event = fake_event()

    async def fake_users(limit=100):
        for uid in (1, 2):
            yield SimpleNamespace(id=uid, name=f"u{uid}", global_name=None, bot=False, avatar=None)

    event.users = fake_users
    guild = guild_with(event)
    result = await event_ops.users(ctx_for(guild, True), {"event_id": 10, "limit": 5})
    assert [u["id"] for u in result] == ["1", "2"]
