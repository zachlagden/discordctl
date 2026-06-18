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


def test_resolve_category_by_id_ignores_non_category_with_same_id():
    from types import SimpleNamespace
    cat = SimpleNamespace(id=300, name="staff")
    other = SimpleNamespace(id=300, name="general")
    guild = SimpleNamespace(categories=[cat], get_channel=lambda cid: other)
    from claude_control.ops.lookup import resolve_category
    assert resolve_category(guild, {"category_id": 300}) is cat


def test_resolve_user_id_requires_arg():
    from claude_control.ops.lookup import resolve_user_id
    from claude_control.ops.registry import HandlerError
    with pytest.raises(HandlerError):
        resolve_user_id({})
    assert resolve_user_id({"user_id": 5}) == 5


async def test_resolve_member_by_id_uses_cache_then_fetch():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from claude_control.ops.lookup import resolve_member
    member = SimpleNamespace(id=100, name="alice")
    guild = SimpleNamespace(get_member=lambda uid: member if uid == 100 else None,
                            fetch_member=AsyncMock())
    assert await resolve_member(guild, {"user_id": 100}) is member
    guild.fetch_member.assert_not_called()
