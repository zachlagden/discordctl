from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discordctl.ops.handlers import template as template_ops
from discordctl.ops.registry import BusContext, HandlerError


def make_template(code="abc", name="base"):
    return SimpleNamespace(
        code=code,
        name=name,
        description="d",
        url="http://x",
        uses=2,
        is_dirty=False,
        creator=None,
        source_guild=None,
        created_at=None,
        updated_at=None,
        sync=AsyncMock(),
        edit=AsyncMock(),
        delete=AsyncMock(),
    )


def make_guild(templates=None):
    return SimpleNamespace(
        id=1,
        roles=[],
        channels=[],
        categories=[],
        templates=AsyncMock(return_value=templates or []),
        create_template=AsyncMock(return_value=make_template()),
    )


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


def bot_for(guild, **extra):
    return SimpleNamespace(get_guild=lambda gid: guild, **extra)


async def test_list_read():
    guild = make_guild(templates=[make_template()])
    result = await template_ops.list_templates(ctx_for(guild, True), {})
    assert result[0]["code"] == "abc"


async def test_get_read():
    guild = make_guild()
    bot = bot_for(guild, fetch_template=AsyncMock(return_value=make_template(code="xyz")))
    result = await template_ops.get(ctx_for(guild, True, bot=bot), {"code": "xyz"})
    bot.fetch_template.assert_awaited_once()
    assert result["code"] == "xyz"


async def test_create_dry_run():
    guild = make_guild()
    result = await template_ops.create(ctx_for(guild, True), {"name": "snap"})
    assert result["planned"] is True
    guild.create_template.assert_not_called()


async def test_create_live():
    guild = make_guild()
    result = await template_ops.create(ctx_for(guild, False), {"name": "snap", "description": "d"})
    guild.create_template.assert_awaited_once()
    assert result["code"] == "abc"


async def test_sync_dry_run():
    tmpl = make_template()
    guild = make_guild(templates=[tmpl])
    result = await template_ops.sync(ctx_for(guild, True), {"code": "abc"})
    assert result["planned"] is True
    tmpl.sync.assert_not_called()


async def test_sync_live_resolves_and_syncs():
    tmpl = make_template()
    tmpl.sync = AsyncMock(return_value=tmpl)
    guild = make_guild(templates=[tmpl])
    await template_ops.sync(ctx_for(guild, False), {"code": "abc"})
    tmpl.sync.assert_awaited_once()


async def test_edit_dry_run():
    tmpl = make_template()
    guild = make_guild(templates=[tmpl])
    result = await template_ops.edit(ctx_for(guild, True), {"code": "abc", "name": "new"})
    assert result["planned"] is True
    tmpl.edit.assert_not_called()


async def test_edit_live():
    tmpl = make_template()
    tmpl.edit = AsyncMock(return_value=tmpl)
    guild = make_guild(templates=[tmpl])
    await template_ops.edit(ctx_for(guild, False), {"code": "abc", "name": "new"})
    tmpl.edit.assert_awaited_once()
    assert tmpl.edit.await_args.kwargs["name"] == "new"


async def test_delete_dry_run():
    tmpl = make_template()
    guild = make_guild(templates=[tmpl])
    result = await template_ops.delete(ctx_for(guild, True), {"code": "abc"})
    assert result["planned"] is True
    tmpl.delete.assert_not_called()


async def test_delete_live():
    tmpl = make_template()
    guild = make_guild(templates=[tmpl])
    result = await template_ops.delete(ctx_for(guild, False), {"code": "abc"})
    tmpl.delete.assert_awaited_once()
    assert result["deleted"] == "abc"


async def test_sync_not_found():
    guild = make_guild(templates=[])
    with pytest.raises(HandlerError):
        await template_ops.sync(ctx_for(guild, False), {"code": "missing"})
