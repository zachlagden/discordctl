import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import soundboard as sb_ops
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


def fake_sound(sid=900, name="boom"):
    return SimpleNamespace(
        id=sid,
        name=name,
        volume=1.0,
        emoji=None,
        available=True,
        guild=SimpleNamespace(id=1),
        user=SimpleNamespace(id=5),
        url="http://x",
        edit=AsyncMock(),
        delete=AsyncMock(),
    )


def guild_with_sounds(sounds, cached=True):
    by_id = {s.id: s for s in sounds}
    return SimpleNamespace(
        id=1,
        soundboard_sounds=sounds if cached else [],
        get_soundboard_sound=lambda sid: by_id.get(sid),
        fetch_soundboard_sounds=AsyncMock(return_value=sounds),
        create_soundboard_sound=AsyncMock(),
    )


async def test_soundboard_list_read():
    guild = guild_with_sounds([fake_sound()])
    result = await sb_ops.list_sounds(ctx_for(guild, True), {})
    assert result["guild"][0]["name"] == "boom"
    assert result["guild"][0]["id"] == "900"


async def test_soundboard_list_include_default():
    guild = guild_with_sounds([fake_sound()])
    bot = SimpleNamespace(
        get_guild=lambda gid: guild,
        fetch_soundboard_default_sounds=AsyncMock(return_value=[fake_sound(1, "wow")]),
    )
    result = await sb_ops.list_sounds(ctx_for(guild, True, bot=bot), {"include_default": True})
    assert result["default"][0]["name"] == "wow"


async def test_soundboard_info_read():
    guild = guild_with_sounds([fake_sound(900, "boom")])
    result = await sb_ops.info(ctx_for(guild, True), {"sound_id": 900})
    assert result["name"] == "boom"


async def test_soundboard_create_dry_run():
    guild = guild_with_sounds([])
    result = await sb_ops.create(
        ctx_for(guild, True), {"name": "n", "sound_b64": base64.b64encode(b"x").decode()}
    )
    assert result["planned"] is True
    guild.create_soundboard_sound.assert_not_called()


async def test_soundboard_create_live():
    new = fake_sound(901, "new")
    guild = guild_with_sounds([])
    guild.create_soundboard_sound = AsyncMock(return_value=new)
    audio = base64.b64encode(b"audiobytes").decode()
    result = await sb_ops.create(
        ctx_for(guild, False),
        {"name": "new", "sound_b64": audio, "volume": 0.5, "emoji": "🔥"},
    )
    assert result["id"] == "901"
    kwargs = guild.create_soundboard_sound.call_args.kwargs
    assert kwargs["sound"] == b"audiobytes"
    assert kwargs["volume"] == 0.5
    assert kwargs["emoji"] is not None


async def test_soundboard_edit_dry_run():
    sound = fake_sound()
    guild = guild_with_sounds([sound])
    result = await sb_ops.edit(ctx_for(guild, True), {"sound_id": 900, "name": "renamed"})
    assert result["planned"] is True
    sound.edit.assert_not_called()


async def test_soundboard_edit_live():
    updated = fake_sound(900, "renamed")
    sound = fake_sound()
    sound.edit = AsyncMock(return_value=updated)
    guild = guild_with_sounds([sound])
    result = await sb_ops.edit(
        ctx_for(guild, False), {"sound_id": 900, "name": "renamed", "volume": 0.8}
    )
    assert result["name"] == "renamed"
    sound.edit.assert_awaited_once()


async def test_soundboard_delete_dry_run():
    sound = fake_sound()
    guild = guild_with_sounds([sound])
    result = await sb_ops.delete(ctx_for(guild, True), {"sound_id": 900})
    assert result["planned"] is True
    sound.delete.assert_not_called()


async def test_soundboard_delete_live():
    sound = fake_sound()
    guild = guild_with_sounds([sound])
    result = await sb_ops.delete(ctx_for(guild, False), {"sound_id": 900, "reason": "r"})
    assert result["deleted"] == "900"
    sound.delete.assert_awaited_once()
