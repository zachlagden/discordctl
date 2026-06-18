from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import voice as voice_ops
from discordctl.ops.registry import BusContext


def ctx_for(guild, dry_run, bot=None):
    return BusContext(
        bot=bot or SimpleNamespace(get_guild=lambda gid: guild),
        dry_run=dry_run,
        confirm=not dry_run,
        yes_really=False,
        actor="t",
        write_enabled=True,
        allowed_guild_ids=frozenset({1}),
        default_guild_id=1,
    )


def guild_with_member(member, bot_member=None):
    bot_member = bot_member or SimpleNamespace(id=10, voice=None)
    members = {member.id: member, bot_member.id: bot_member}
    return SimpleNamespace(
        id=1,
        me=bot_member,
        get_member=lambda uid: members.get(uid),
        fetch_member=AsyncMock(),
    )


async def test_state_get_other_user():
    voice = SimpleNamespace(
        channel=SimpleNamespace(id=300),
        mute=False,
        deaf=False,
        self_mute=True,
        self_deaf=False,
        self_stream=False,
        self_video=False,
        suppress=False,
        afk=False,
        requested_to_speak_at=None,
        session_id="sess",
    )
    member = SimpleNamespace(id=42, voice=voice)
    guild = guild_with_member(member)
    result = await voice_ops.state_get(ctx_for(guild, True), {"user_id": 42})
    assert result["channel_id"] == "300"
    assert result["self_mute"] is True
    assert result["connected"] is True
    assert result["user_id"] == "42"


async def test_state_get_defaults_to_bot():
    bot_member = SimpleNamespace(id=10, voice=None)
    member = SimpleNamespace(id=42, voice=None)
    guild = guild_with_member(member, bot_member=bot_member)
    result = await voice_ops.state_get(ctx_for(guild, True), {})
    assert result["user_id"] == "10"
    assert result["connected"] is False


async def test_state_self_set_dry_run():
    bot = SimpleNamespace(get_guild=lambda gid: None, http=SimpleNamespace(request=AsyncMock()))
    guild = SimpleNamespace(id=1, me=SimpleNamespace(id=10))
    bot.get_guild = lambda gid: guild
    result = await voice_ops.state_self_set(ctx_for(guild, True, bot=bot), {"suppress": False})
    assert result["planned"] is True
    bot.http.request.assert_not_called()


async def test_state_self_set_live_http():
    request = AsyncMock()
    bot = SimpleNamespace(get_guild=lambda gid: None, http=SimpleNamespace(request=request))
    guild = SimpleNamespace(id=1, me=SimpleNamespace(id=10))
    bot.get_guild = lambda gid: guild
    await voice_ops.state_self_set(
        ctx_for(guild, False, bot=bot), {"channel_id": 300, "request_to_speak": True}
    )
    request.assert_awaited_once()
    route = request.call_args.args[0]
    assert route.method == "PATCH"
    assert "/voice-states/@me" in route.path
    payload = request.call_args.kwargs["json"]
    assert payload["channel_id"] == "300"
    assert "request_to_speak_timestamp" in payload


async def test_state_set_other_live_http():
    request = AsyncMock()
    bot = SimpleNamespace(get_guild=lambda gid: None, http=SimpleNamespace(request=request))
    guild = SimpleNamespace(id=1, me=SimpleNamespace(id=10))
    bot.get_guild = lambda gid: guild
    await voice_ops.state_set(ctx_for(guild, False, bot=bot), {"user_id": 42, "suppress": True})
    request.assert_awaited_once()
    route = request.call_args.args[0]
    assert route.method == "PATCH"
    payload = request.call_args.kwargs["json"]
    assert payload["suppress"] is True


async def test_state_set_dry_run():
    request = AsyncMock()
    bot = SimpleNamespace(get_guild=lambda gid: None, http=SimpleNamespace(request=request))
    guild = SimpleNamespace(id=1, me=SimpleNamespace(id=10))
    bot.get_guild = lambda gid: guild
    result = await voice_ops.state_set(
        ctx_for(guild, True, bot=bot), {"user_id": 42, "suppress": True}
    )
    assert result["planned"] is True
    request.assert_not_called()
