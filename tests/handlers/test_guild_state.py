from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from claude_control.ops.handlers.guild_state import apply, build_snapshot, diff_snapshots
from claude_control.ops.registry import BusContext, HandlerError


def _role(rid, name):
    return SimpleNamespace(id=rid, name=name, position=rid, hoist=False, mentionable=False,
                           managed=False, color=SimpleNamespace(value=0),
                           permissions=SimpleNamespace(value=0))


def make_guild(role_names):
    roles = [_role(i + 1, name) for i, name in enumerate(role_names)]
    return SimpleNamespace(id=1, name="DigiGrow", owner_id=5, member_count=42, description=None,
                           roles=roles, categories=[], channels=[],
                           create_role=AsyncMock(return_value=_role(99, "created")))


def ctx_for(guild, dry_run, yes_really):
    return BusContext(bot=SimpleNamespace(get_guild=lambda gid: guild),
                      dry_run=dry_run, confirm=not dry_run, yes_really=yes_really, actor="t",
                      write_enabled=True, allowed_guild_ids=frozenset({1}), default_guild_id=1)


def test_diff_detects_create_and_delete():
    current = {"roles": [{"name": "mod"}], "categories": [], "channels": []}
    desired = {"roles": [{"name": "admin"}], "categories": [], "channels": []}
    result = diff_snapshots(current, desired)
    assert result["roles"]["create"] == [{"name": "admin"}]
    assert result["roles"]["delete"] == [{"name": "mod"}]


def test_diff_detects_no_change():
    snap = {"roles": [{"name": "mod"}], "categories": [], "channels": []}
    result = diff_snapshots(snap, snap)
    assert result["roles"]["create"] == []
    assert result["roles"]["delete"] == []


async def test_apply_requires_desired():
    guild = make_guild(["old"])
    with pytest.raises(HandlerError) as exc:
        await apply(ctx_for(guild, False, True), {})
    assert exc.value.code == "bad_args"


async def test_apply_deletion_needs_yes_really_even_when_dry_run():
    guild = make_guild(["old"])
    desired = build_snapshot(guild)
    desired["roles"] = []
    with pytest.raises(HandlerError) as exc:
        await apply(ctx_for(guild, True, False), {"desired": desired})
    assert exc.value.code == "needs_yes_really"


async def test_apply_dry_run_does_not_create():
    guild = make_guild([])
    desired = build_snapshot(guild)
    desired["roles"] = [_dict_role("new")]
    result = await apply(ctx_for(guild, True, False), {"desired": desired})
    assert result["planned"] is True
    guild.create_role.assert_not_awaited()


async def test_apply_live_creates_role():
    guild = make_guild([])
    desired = build_snapshot(guild)
    desired["roles"] = [_dict_role("new")]
    await apply(ctx_for(guild, False, False), {"desired": desired})
    guild.create_role.assert_awaited_once()


def _dict_role(name):
    return {"id": None, "name": name, "position": 0, "color": "#000000", "hoist": False,
            "mentionable": False, "managed": False, "permissions": "0"}
