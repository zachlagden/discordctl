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


async def test_audit_log():
    entry1 = SimpleNamespace(action="role_create", user=None, target=None, reason=None,
                             created_at="2026-06-18")
    entry2 = SimpleNamespace(action="role_delete", user=SimpleNamespace(id=5),
                             target=SimpleNamespace(id=7), reason="cleanup",
                             created_at="2026-06-18")

    async def gen(entries):
        for entry in entries:
            yield entry

    guild = make_guild()
    guild.audit_logs = lambda limit: gen([entry1, entry2])
    result = await guild_ops.audit_log(ctx_for(guild, True), {})

    assert len(result) == 2
    assert result[0]["user_id"] is None
    assert result[0]["target_id"] is None
    assert result[1]["user_id"] == "5"
    assert result[1]["target_id"] == "7"
    for item in result:
        assert set(item) == {"action", "user_id", "target_id", "reason", "created_at"}
