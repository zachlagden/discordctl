from types import SimpleNamespace

import pytest

from claude_control.ops.lookup import resolve_guild, resolve_role
from claude_control.ops.registry import BusContext, HandlerError


def make_ctx(bot, allowed=frozenset({1}), default=1):
    return BusContext(
        bot=bot, dry_run=True, confirm=False, yes_really=False, actor="t",
        write_enabled=True, allowed_guild_ids=allowed, default_guild_id=default,
    )


def test_resolve_guild_uses_default_when_absent():
    guild = SimpleNamespace(id=1, roles=[])
    bot = SimpleNamespace(get_guild=lambda gid: guild if gid == 1 else None)
    ctx = make_ctx(bot)
    assert resolve_guild(ctx, {}) is guild


def test_resolve_guild_rejects_non_allowlisted():
    guild = SimpleNamespace(id=999)
    bot = SimpleNamespace(get_guild=lambda gid: guild)
    ctx = make_ctx(bot, allowed=frozenset({1}), default=None)
    with pytest.raises(HandlerError):
        resolve_guild(ctx, {"guild_id": 999})


def test_resolve_role_by_name_ambiguous():
    r1 = SimpleNamespace(id=10, name="mod")
    r2 = SimpleNamespace(id=11, name="mod")
    guild = SimpleNamespace(roles=[r1, r2], get_role=lambda rid: None)
    with pytest.raises(HandlerError):
        resolve_role(guild, {"role_name": "mod"})


def test_resolve_role_by_id():
    role = SimpleNamespace(id=10, name="mod")
    guild = SimpleNamespace(roles=[role], get_role=lambda rid: role if rid == 10 else None)
    assert resolve_role(guild, {"role_id": 10}) is role
