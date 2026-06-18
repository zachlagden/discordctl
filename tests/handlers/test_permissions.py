from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discordctl.ops.handlers import permissions as perm_ops
from discordctl.ops.registry import BusContext


def make_guild():
    role = SimpleNamespace(id=10, name="mod")
    channel = SimpleNamespace(
        id=200,
        name="general",
        type=SimpleNamespace(name="text"),
        overwrites={},
        set_permissions=AsyncMock(),
    )
    guild = SimpleNamespace(
        id=1,
        roles=[role],
        channels=[channel],
        get_role=lambda rid: role if rid == 10 else None,
        get_channel=lambda cid: channel if cid == 200 else None,
    )
    return guild, channel, role


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


async def test_overwrite_set_dry_run():
    guild, channel, role = make_guild()
    result = await perm_ops.channel_overwrite_set(
        ctx_for(guild, True),
        {"channel_id": 200, "role_id": 10, "allow": ["send_messages"], "deny": []},
    )
    assert result["planned"] is True
    channel.set_permissions.assert_not_called()


async def test_overwrite_clear_live():
    guild, channel, role = make_guild()
    await perm_ops.channel_overwrite_clear(
        ctx_for(guild, False), {"channel_id": 200, "role_id": 10}
    )
    channel.set_permissions.assert_awaited_once()


async def test_overwrite_set_uncached_member_raises_not_found():
    from unittest.mock import AsyncMock
    import discord
    from discordctl.ops.registry import HandlerError

    channel = SimpleNamespace(
        id=200,
        name="general",
        type=SimpleNamespace(name="text"),
        overwrites={},
        set_permissions=AsyncMock(),
    )
    resp = SimpleNamespace(status=404, reason="Not Found", headers={})

    async def boom(uid):
        raise discord.NotFound(resp, "Unknown Member")

    guild = SimpleNamespace(
        id=1,
        roles=[],
        channels=[channel],
        get_member=lambda uid: None,
        fetch_member=boom,
        get_channel=lambda cid: channel if cid == 200 else None,
    )
    with pytest.raises(HandlerError) as ei:
        await perm_ops.channel_overwrite_set(
            ctx_for(guild, False), {"channel_id": 200, "user_id": 999, "allow": [], "deny": []}
        )
    assert ei.value.code == "not_found"


async def test_overwrite_set_invalid_permission_raises_bad_args():
    from discordctl.ops.registry import HandlerError

    guild, channel, role = make_guild()
    with pytest.raises(HandlerError) as ei:
        await perm_ops.channel_overwrite_set(
            ctx_for(guild, False),
            {"channel_id": 200, "role_id": 10, "allow": ["not_a_real_perm"], "deny": []},
        )
    assert ei.value.code == "bad_args"
