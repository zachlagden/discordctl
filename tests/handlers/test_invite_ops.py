from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord

from discordctl.ops.handlers import invite as invite_ops
from discordctl.ops.registry import BusContext


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


def fake_invite(code="abc"):
    return SimpleNamespace(
        code=code,
        url=f"https://discord.gg/{code}",
        uses=3,
        max_uses=10,
        max_age=3600,
        temporary=False,
        revoked=False,
        channel=SimpleNamespace(id=200),
        guild=SimpleNamespace(id=1),
        approximate_member_count=42,
        approximate_presence_count=7,
        expires_at=None,
        created_at=None,
        inviter=SimpleNamespace(id=99),
        target_type=None,
        target_user=None,
        target_application=None,
    )


async def test_invite_info_read():
    inv = fake_invite("xyz")
    bot = SimpleNamespace(get_guild=lambda gid: None, fetch_invite=AsyncMock(return_value=inv))
    result = await invite_ops.info(ctx_for(None, True, bot=bot), {"code": "xyz"})
    assert result["code"] == "xyz"
    assert result["approximate_member_count"] == 42
    assert result["approximate_presence_count"] == 7
    bot.fetch_invite.assert_awaited_once()


async def test_invite_list_guild_read():
    inv = fake_invite("a")
    guild = SimpleNamespace(id=1, invites=AsyncMock(return_value=[inv]))
    result = await invite_ops.list_guild(ctx_for(guild, True), {})
    assert result[0]["code"] == "a"
    assert result[0]["max_age"] == 3600


async def test_invite_create_dry_run():
    channel = SimpleNamespace(
        id=200, name="general", type=SimpleNamespace(name="text"), create_invite=AsyncMock()
    )
    guild = SimpleNamespace(
        id=1, channels=[channel], get_channel=lambda cid: channel if cid == 200 else None
    )
    result = await invite_ops.create(ctx_for(guild, True), {"channel_id": 200, "max_age": 60})
    assert result["planned"] is True
    channel.create_invite.assert_not_called()


async def test_invite_create_live_full_args():
    inv = fake_invite("new")
    channel = SimpleNamespace(
        id=200,
        name="general",
        type=SimpleNamespace(name="text"),
        create_invite=AsyncMock(return_value=inv),
    )
    member = SimpleNamespace(id=555)
    guild = SimpleNamespace(
        id=1,
        channels=[channel],
        get_channel=lambda cid: channel if cid == 200 else None,
        get_member=lambda uid: member if uid == 555 else None,
    )
    await invite_ops.create(
        ctx_for(guild, False),
        {
            "channel_id": 200,
            "max_age": 60,
            "max_uses": 5,
            "temporary": True,
            "unique": True,
            "target_type": "stream",
            "target_user_id": 555,
            "reason": "r",
        },
    )
    channel.create_invite.assert_awaited_once()
    kwargs = channel.create_invite.call_args.kwargs
    assert kwargs["max_age"] == 60
    assert kwargs["max_uses"] == 5
    assert kwargs["temporary"] is True
    assert kwargs["unique"] is True
    assert kwargs["target_type"] is discord.InviteTarget.stream
    assert kwargs["target_user"] is member
    assert kwargs["reason"] == "r"
