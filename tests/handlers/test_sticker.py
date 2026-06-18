import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import sticker as sticker_ops
from discordctl.ops.registry import BusContext


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


def make_sticker(sid=10, name="party"):
    return SimpleNamespace(
        id=sid,
        name=name,
        description="d",
        emoji="🎉",
        format=SimpleNamespace(name="png"),
        available=True,
        guild_id=1,
        edit=AsyncMock(),
        delete=AsyncMock(),
    )


async def test_sticker_list():
    guild = SimpleNamespace(id=1, stickers=[make_sticker()])
    result = await sticker_ops.list_stickers(ctx_for(guild, True), {})
    assert result[0]["name"] == "party"
    assert result[0]["emoji"] == "🎉"


async def test_sticker_create_dry_run():
    guild = SimpleNamespace(id=1, stickers=[], create_sticker=AsyncMock())
    result = await sticker_ops.create(
        ctx_for(guild, True),
        {"name": "party", "emoji": "🎉", "file_b64": base64.b64encode(b"img").decode()},
    )
    assert result["planned"] is True
    guild.create_sticker.assert_not_called()


async def test_sticker_create_live():
    created = make_sticker(sid=99, name="new")
    guild = SimpleNamespace(id=1, stickers=[], create_sticker=AsyncMock(return_value=created))
    result = await sticker_ops.create(
        ctx_for(guild, False),
        {"name": "new", "emoji": "🎉", "file_b64": base64.b64encode(b"img").decode()},
    )
    guild.create_sticker.assert_awaited_once()
    assert result["id"] == "99"


async def test_sticker_edit_live():
    sticker = make_sticker()
    sticker.edit.return_value = sticker
    guild = SimpleNamespace(id=1, stickers=[sticker])
    await sticker_ops.edit(ctx_for(guild, False), {"sticker_id": 10, "name": "renamed"})
    sticker.edit.assert_awaited_once()
    assert sticker.edit.await_args.kwargs["name"] == "renamed"


async def test_sticker_delete_dry_then_live():
    sticker = make_sticker()
    guild = SimpleNamespace(id=1, stickers=[sticker])
    dry = await sticker_ops.delete(ctx_for(guild, True), {"sticker_id": 10})
    assert dry["planned"] is True
    sticker.delete.assert_not_called()
    live = await sticker_ops.delete(ctx_for(guild, False), {"sticker_id": 10})
    assert live["deleted"] is True
    sticker.delete.assert_awaited_once()


async def test_sticker_get_global():
    fetched = make_sticker(sid=500, name="g")
    bot = SimpleNamespace(get_guild=lambda gid: None, fetch_sticker=AsyncMock(return_value=fetched))
    result = await sticker_ops.get(ctx_for(None, True, bot=bot), {"sticker_id": 500})
    assert result["id"] == "500"


async def test_sticker_packs():
    pack = SimpleNamespace(
        id=1, name="pack", stickers=[SimpleNamespace(id=3), SimpleNamespace(id=4)]
    )
    bot = SimpleNamespace(
        get_guild=lambda gid: None,
        fetch_premium_sticker_packs=AsyncMock(return_value=[pack]),
    )
    result = await sticker_ops.packs(ctx_for(None, True, bot=bot), {})
    assert result[0]["sticker_ids"] == ["3", "4"]
