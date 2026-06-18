import base64

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discordctl.ops.handlers import emoji as emoji_ops
from discordctl.ops.registry import BusContext, HandlerError


def make_emoji(eid=1, name="smile"):
    return SimpleNamespace(id=eid, name=name, animated=False, edit=AsyncMock(), delete=AsyncMock())


def make_guild(emoji):
    role = SimpleNamespace(id=99, name="vip")
    return SimpleNamespace(
        id=1,
        emojis=[emoji],
        get_role=lambda rid: role if rid == 99 else None,
    )


def ctx_for(guild, dry_run, bot=None):
    return BusContext(
        bot=bot if bot is not None else SimpleNamespace(get_guild=lambda gid: guild),
        dry_run=dry_run,
        confirm=not dry_run,
        yes_really=False,
        actor="t",
        write_enabled=True,
        allowed_guild_ids=frozenset({1}),
        default_guild_id=1,
    )


async def test_emoji_info():
    emoji = make_emoji()
    guild = make_guild(emoji)
    bot = SimpleNamespace(get_guild=lambda gid: guild)
    result = await emoji_ops.info(ctx_for(guild, True, bot), {"emoji_id": 1})
    assert result["name"] == "smile"


async def test_emoji_info_not_found():
    emoji = make_emoji()
    guild = make_guild(emoji)
    bot = SimpleNamespace(get_guild=lambda gid: guild)
    with pytest.raises(HandlerError) as exc:
        await emoji_ops.info(ctx_for(guild, True, bot), {"emoji_id": 555})
    assert exc.value.code == "not_found"


async def test_emoji_edit_dry_run_does_not_call():
    emoji = make_emoji()
    guild = make_guild(emoji)
    bot = SimpleNamespace(get_guild=lambda gid: guild)
    result = await emoji_ops.edit(ctx_for(guild, True, bot), {"emoji_id": 1, "name": "grin"})
    assert result["planned"] is True
    emoji.edit.assert_not_called()


async def test_emoji_edit_live_maps_roles():
    emoji = make_emoji()
    guild = make_guild(emoji)
    bot = SimpleNamespace(get_guild=lambda gid: guild)
    await emoji_ops.edit(ctx_for(guild, False, bot), {"emoji_id": 1, "name": "grin", "roles": [99]})
    kwargs = emoji.edit.await_args.kwargs
    assert kwargs["name"] == "grin"
    assert kwargs["roles"][0].id == 99


async def test_emoji_edit_not_found():
    emoji = make_emoji()
    guild = make_guild(emoji)
    bot = SimpleNamespace(get_guild=lambda gid: guild)
    with pytest.raises(HandlerError) as exc:
        await emoji_ops.edit(ctx_for(guild, False, bot), {"emoji_id": 42, "name": "x"})
    assert exc.value.code == "not_found"


async def test_app_list():
    bot = SimpleNamespace(
        get_guild=lambda gid: None,
        fetch_application_emojis=AsyncMock(return_value=[make_emoji(7, "appemoji")]),
    )
    result = await emoji_ops.app_list(ctx_for(None, True, bot), {})
    assert result[0]["name"] == "appemoji"
    bot.fetch_application_emojis.assert_awaited_once()


async def test_app_info():
    bot = SimpleNamespace(
        get_guild=lambda gid: None,
        fetch_application_emoji=AsyncMock(return_value=make_emoji(7, "appemoji")),
    )
    result = await emoji_ops.app_info(ctx_for(None, True, bot), {"emoji_id": 7})
    assert result["id"] == "7"
    bot.fetch_application_emoji.assert_awaited_once_with(7)


async def test_app_create_dry_run_does_not_call():
    bot = SimpleNamespace(get_guild=lambda gid: None, create_application_emoji=AsyncMock())
    raw = base64.b64encode(b"PNG").decode()
    result = await emoji_ops.app_create(ctx_for(None, True, bot), {"name": "new", "image_b64": raw})
    assert result["planned"] is True
    bot.create_application_emoji.assert_not_called()


async def test_app_create_live():
    created = make_emoji(8, "new")
    bot = SimpleNamespace(
        get_guild=lambda gid: None,
        create_application_emoji=AsyncMock(return_value=created),
    )
    raw = base64.b64encode(b"PNG").decode()
    await emoji_ops.app_create(ctx_for(None, False, bot), {"name": "new", "image_b64": raw})
    kwargs = bot.create_application_emoji.await_args.kwargs
    assert kwargs["name"] == "new"
    assert kwargs["image"] == b"PNG"


async def test_app_edit_live():
    fetched = make_emoji(8, "old")
    fetched.edit = AsyncMock(return_value=make_emoji(8, "renamed"))
    bot = SimpleNamespace(
        get_guild=lambda gid: None,
        fetch_application_emoji=AsyncMock(return_value=fetched),
    )
    result = await emoji_ops.app_edit(ctx_for(None, False, bot), {"emoji_id": 8, "name": "renamed"})
    assert result["name"] == "renamed"
    fetched.edit.assert_awaited_once_with(name="renamed")


async def test_app_delete_dry_vs_live():
    fetched = make_emoji(8, "old")
    bot = SimpleNamespace(
        get_guild=lambda gid: None,
        fetch_application_emoji=AsyncMock(return_value=fetched),
    )
    result = await emoji_ops.app_delete(ctx_for(None, True, bot), {"emoji_id": 8})
    assert result["planned"] is True
    bot.fetch_application_emoji.assert_not_called()

    out = await emoji_ops.app_delete(ctx_for(None, False, bot), {"emoji_id": 8})
    assert out["deleted"] == "8"
    fetched.delete.assert_awaited_once()
