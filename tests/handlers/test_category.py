from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import category as cat_ops
from discordctl.ops.registry import BusContext


def make_guild():
    cat = SimpleNamespace(
        id=300, name="staff", position=0, channels=[], edit=AsyncMock(), delete=AsyncMock()
    )
    guild = SimpleNamespace(
        id=1,
        categories=[cat],
        channels=[cat],
        get_channel=lambda cid: cat if cid == 300 else None,
        create_category=AsyncMock(return_value=cat),
    )
    return guild, cat


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
    guild, cat = make_guild()
    result = await cat_ops.create(ctx_for(guild, True), {"name": "new"})
    assert result["planned"] is True
    guild.create_category.assert_not_called()


async def test_delete_live():
    guild, cat = make_guild()
    await cat_ops.delete(ctx_for(guild, False), {"category_id": 300})
    cat.delete.assert_awaited_once()
