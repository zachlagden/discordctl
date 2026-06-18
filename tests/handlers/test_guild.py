from types import SimpleNamespace
from unittest.mock import AsyncMock

from claude_control.ops.handlers import guild as guild_ops
from claude_control.ops.registry import BusContext


def make_guild():
    guild = SimpleNamespace(id=1, name="DigiGrow", owner_id=5, member_count=42,
                            description=None, roles=[1, 2], channels=[1, 2, 3],
                            categories=[1], edit=AsyncMock())
    return guild


def ctx_for(guild, dry_run):
    return BusContext(bot=SimpleNamespace(get_guild=lambda gid: guild),
                      dry_run=dry_run, confirm=not dry_run, yes_really=False, actor="t",
                      write_enabled=True, allowed_guild_ids=frozenset({1}), default_guild_id=1)


async def test_info_counts():
    guild = make_guild()
    result = await guild_ops.info(ctx_for(guild, True), {})
    assert result["name"] == "DigiGrow"
    assert result["counts"]["channels"] == 3


async def test_edit_dry_run():
    guild = make_guild()
    result = await guild_ops.edit(ctx_for(guild, True), {"name": "New"})
    assert result["planned"] is True
    guild.edit.assert_not_called()
