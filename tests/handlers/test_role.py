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


async def test_create_icon_and_unicode_emoji():
    import base64

    guild, role = make_guild()
    raw = base64.b64encode(b"PNGDATA").decode()
    await role_ops.create(ctx_for(guild, False), {"name": "c", "icon": raw})
    assert guild.create_role.await_args.kwargs["display_icon"] == b"PNGDATA"

    guild, role = make_guild()
    await role_ops.create(ctx_for(guild, False), {"name": "c", "unicode_emoji": "🔥"})
    assert guild.create_role.await_args.kwargs["display_icon"] == "🔥"


async def test_create_gradient_colors_maps_kwargs():
    guild, role = make_guild()
    await role_ops.create(
        ctx_for(guild, False),
        {"name": "c", "colors": {"primary": "#ff0000", "secondary": 65280, "tertiary": "#0000ff"}},
    )
    kwargs = guild.create_role.await_args.kwargs
    assert kwargs["colour"].value == 0xFF0000
    assert kwargs["secondary_colour"].value == 65280
    assert kwargs["tertiary_colour"].value == 0x0000FF


async def test_edit_permissions_and_emoji_live():
    guild, role = make_guild()
    await role_ops.edit(
        ctx_for(guild, False),
        {"role_id": 10, "permissions": "8", "unicode_emoji": "⭐"},
    )
    kwargs = role.edit.await_args.kwargs
    assert kwargs["permissions"].value == 8
    assert kwargs["display_icon"] == "⭐"


async def test_edit_position_forwarded_to_role_edit():
    guild, role = make_guild()
    await role_ops.edit(ctx_for(guild, False), {"role_id": 10, "position": 3})
    kwargs = role.edit.await_args.kwargs
    assert kwargs["position"] == 3


async def test_create_ignores_position():
    guild, role = make_guild()
    await role_ops.create(ctx_for(guild, False), {"name": "c", "position": 5})
    assert "position" not in guild.create_role.await_args.kwargs


async def test_edit_gradient_dry_run_does_not_call():
    guild, role = make_guild()
    result = await role_ops.edit(
        ctx_for(guild, True),
        {"role_id": 10, "colors": {"primary": 255}},
    )
    assert result["planned"] is True
    assert "secondary_colour" not in result["fields"]
    assert "colour" in result["fields"]
    role.edit.assert_not_called()
