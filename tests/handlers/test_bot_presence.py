import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from discordctl.ops.handlers import bot as bot_ops
from discordctl.ops.registry import BusContext, HandlerError


def make_bot():
    return SimpleNamespace(
        change_presence=AsyncMock(),
        user=SimpleNamespace(
            id=42,
            name="ctl",
            global_name=None,
            bot=True,
            avatar=None,
            edit=AsyncMock(),
        ),
        http=SimpleNamespace(
            get_bot_gateway=AsyncMock(return_value=(1, "wss://x", {"total": 1000}))
        ),
        latency=0.05,
        shard_count=None,
    )


def ctx_for(bot, dry_run, yes_really=False, guild=None):
    return BusContext(
        bot=bot,
        dry_run=dry_run,
        confirm=not dry_run,
        yes_really=yes_really,
        actor="t",
        write_enabled=True,
        allowed_guild_ids=frozenset({1}),
        default_guild_id=1,
    )


async def test_presence_set_dry_run_does_not_change():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=True)
    result = await bot_ops.presence_set(ctx, {"type": "playing", "name": "chess"})
    assert result["planned"] is True
    bot.change_presence.assert_not_called()
    assert not hasattr(bot, "presence_state")


async def test_presence_set_live_builds_game_and_calls():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=False)
    result = await bot_ops.presence_set(ctx, {"type": "playing", "name": "chess", "status": "dnd"})
    bot.change_presence.assert_awaited_once()
    kwargs = bot.change_presence.await_args.kwargs
    assert isinstance(kwargs["activity"], discord.Game)
    assert kwargs["activity"].name == "chess"
    assert kwargs["status"] == discord.Status.dnd
    assert bot.presence_state == result
    assert result["type"] == "playing"


async def test_presence_set_streaming_passes_url():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=False)
    await bot_ops.presence_set(
        ctx, {"type": "streaming", "name": "live", "url": "https://twitch.tv/x"}
    )
    activity = bot.change_presence.await_args.kwargs["activity"]
    assert isinstance(activity, discord.Streaming)
    assert activity.url == "https://twitch.tv/x"


async def test_presence_set_custom_builds_custom_activity():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=False)
    await bot_ops.presence_set(ctx, {"type": "custom", "name": "vibing"})
    activity = bot.change_presence.await_args.kwargs["activity"]
    assert isinstance(activity, discord.CustomActivity)


async def test_presence_set_rejects_unknown_type():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=False)
    with pytest.raises(HandlerError) as exc:
        await bot_ops.presence_set(ctx, {"type": "sleeping", "name": "x"})
    assert exc.value.code == "bad_args"
    bot.change_presence.assert_not_called()


async def test_presence_set_rejects_unknown_status():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=False)
    with pytest.raises(HandlerError) as exc:
        await bot_ops.presence_set(ctx, {"type": "playing", "name": "x", "status": "asleep"})
    assert exc.value.code == "bad_args"


async def test_presence_clear_dry_run():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=True)
    result = await bot_ops.presence_clear(ctx, {})
    assert result["planned"] is True
    bot.change_presence.assert_not_called()


async def test_presence_clear_live():
    bot = make_bot()
    bot.presence_state = {"type": "playing"}
    ctx = ctx_for(bot, dry_run=False)
    result = await bot_ops.presence_clear(ctx, {})
    bot.change_presence.assert_awaited_once()
    kwargs = bot.change_presence.await_args.kwargs
    assert kwargs["activity"] is None
    assert kwargs["status"] == discord.Status.online
    assert bot.presence_state is None
    assert result == {"presence": None}


async def test_presence_get_unset():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=False)
    assert await bot_ops.presence_get(ctx, {}) == {"presence": None}


async def test_presence_get_reflects_stored_state():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=False)
    await bot_ops.presence_set(ctx, {"type": "watching", "name": "you"})
    assert await bot_ops.presence_get(ctx, {}) == bot.presence_state


async def test_profile_edit_dry_run():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=True)
    result = await bot_ops.profile_edit(ctx, {"username": "newname"})
    assert result["planned"] is True
    bot.user.edit.assert_not_called()


async def test_profile_edit_live_decodes_avatar():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=False)
    raw = b"avatarbytes"
    await bot_ops.profile_edit(
        ctx, {"username": "newname", "avatar_b64": base64.b64encode(raw).decode()}
    )
    bot.user.edit.assert_awaited_once()
    kwargs = bot.user.edit.await_args.kwargs
    assert kwargs["username"] == "newname"
    assert kwargs["avatar"] == raw


async def test_leave_guild_needs_yes_really():
    bot = make_bot()
    guild = SimpleNamespace(id=1, name="g", leave=AsyncMock())
    bot.get_guild = lambda gid: guild
    ctx = ctx_for(bot, dry_run=False, yes_really=False)
    with pytest.raises(HandlerError) as exc:
        await bot_ops.leave_guild(ctx, {"guild_id": 1})
    assert exc.value.code == "needs_yes_really"
    guild.leave.assert_not_called()


async def test_leave_guild_dry_run_does_not_leave():
    bot = make_bot()
    guild = SimpleNamespace(id=1, name="g", leave=AsyncMock())
    bot.get_guild = lambda gid: guild
    ctx = ctx_for(bot, dry_run=True, yes_really=True)
    result = await bot_ops.leave_guild(ctx, {"guild_id": 1})
    assert result["planned"] is True
    guild.leave.assert_not_called()


async def test_leave_guild_live_leaves():
    bot = make_bot()
    guild = SimpleNamespace(id=1, name="g", leave=AsyncMock())
    bot.get_guild = lambda gid: guild
    ctx = ctx_for(bot, dry_run=False, yes_really=True)
    result = await bot_ops.leave_guild(ctx, {"guild_id": 1})
    guild.leave.assert_awaited_once()
    assert result == {"left": "1"}


async def test_gateway_returns_metadata():
    bot = make_bot()
    ctx = ctx_for(bot, dry_run=False)
    result = await bot_ops.gateway(ctx, {})
    assert result["url"] == "wss://x"
    assert result["shards"] == 1
    assert result["session_start_limit"] == {"total": 1000}


async def test_gateway_falls_back_on_error():
    bot = make_bot()
    bot.http.get_bot_gateway = AsyncMock(side_effect=RuntimeError("boom"))
    ctx = ctx_for(bot, dry_run=False)
    result = await bot_ops.gateway(ctx, {})
    assert result["latency_ms"] == 50
    assert result["shard_count"] is None
