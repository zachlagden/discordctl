from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import role as role_ops
from discordctl.ops.registry import BusContext


def make_guild():
    role = SimpleNamespace(
        id=10,
        name="mod",
        position=2,
        hoist=False,
        mentionable=True,
        managed=False,
        color=SimpleNamespace(value=0x5865F2),
        permissions=SimpleNamespace(value=8),
        edit=AsyncMock(),
        delete=AsyncMock(),
    )
    guild = SimpleNamespace(
        id=1,
        roles=[role],
        get_role=lambda rid: role if rid == 10 else None,
        create_role=AsyncMock(return_value=role),
    )
    return guild, role


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
    guild, role = make_guild()
    result = await role_ops.create(ctx_for(guild, True), {"name": "newrole"})
    assert result["planned"] is True
    guild.create_role.assert_not_called()


async def test_permissions_set_live():
    guild, role = make_guild()
    await role_ops.permissions_set(ctx_for(guild, False), {"role_id": 10, "permissions": "8"})
    role.edit.assert_awaited_once()


async def test_create_int_colour_is_decimal_not_hex():
    guild, role = make_guild()
    await role_ops.create(ctx_for(guild, False), {"name": "c", "colour": 16711680})
    kwargs = guild.create_role.await_args.kwargs
    assert kwargs["colour"].value == 16711680
