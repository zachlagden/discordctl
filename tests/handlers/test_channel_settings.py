from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import channel as channel_ops
from discordctl.ops.registry import BusContext


class Target:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __hash__(self):
        return self.id


def make_guild(channel_type="text"):
    ch = SimpleNamespace(
        id=200,
        name="general",
        position=0,
        type=SimpleNamespace(name=channel_type),
        category_id=None,
        topic=None,
        nsfw=False,
        slowmode_delay=0,
        edit=AsyncMock(),
        follow=AsyncMock(return_value=SimpleNamespace(id=999)),
    )
    role = Target(50, "mods")
    member = Target(77, "alice")
    guild = SimpleNamespace(
        id=1,
        channels=[ch],
        get_channel=lambda cid: ch if cid in (200, 300) else None,
        get_role=lambda rid: role if rid == 50 else None,
        get_member=lambda uid: member if uid == 77 else None,
        create_voice_channel=AsyncMock(return_value=ch),
        create_text_channel=AsyncMock(return_value=ch),
    )
    return guild, ch


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


async def test_create_voice_with_fields_live():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=False)
    await channel_ops.create(
        ctx,
        {"name": "vc", "type": "voice", "bitrate": 64000, "user_limit": 5},
    )
    guild.create_voice_channel.assert_awaited_once()
    kwargs = guild.create_voice_channel.await_args.kwargs
    assert kwargs["bitrate"] == 64000
    assert kwargs["user_limit"] == 5


async def test_create_with_permission_overwrites_builds_dict():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=False)
    await channel_ops.create(
        ctx,
        {
            "name": "t",
            "type": "text",
            "permission_overwrites": [
                {"role_id": 50, "allow": ["view_channel"], "deny": ["send_messages"]},
                {"user_id": 77, "allow": ["read_message_history"]},
            ],
        },
    )
    overwrites = guild.create_text_channel.await_args.kwargs["overwrites"]
    targets = {t.id for t in overwrites}
    assert targets == {50, 77}


async def test_edit_live_whitelist_only_provided_fields():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=False)
    await channel_ops.edit(
        ctx, {"channel_id": 200, "topic": "hi", "slowmode_delay": 10, "unknown": "x"}
    )
    ch.edit.assert_awaited_once_with(reason=None, topic="hi", slowmode_delay=10)


async def test_edit_dry_run_no_call():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=True)
    result = await channel_ops.edit(ctx, {"channel_id": 200, "topic": "hi"})
    assert result["planned"] is True
    ch.edit.assert_not_awaited()


async def test_follow_dry_run():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=True)
    result = await channel_ops.follow(ctx, {"channel_id": 200, "target_channel_id": 300})
    assert result["planned"] is True
    ch.follow.assert_not_awaited()


async def test_follow_live():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=False)
    result = await channel_ops.follow(ctx, {"channel_id": 200, "target_channel_id": 300})
    ch.follow.assert_awaited_once()
    assert result["webhook_id"] == "999"


async def test_voice_status_set_dry_run():
    guild, ch = make_guild("voice")
    ctx = ctx_for(guild, dry_run=True)
    result = await channel_ops.voice_status_set(ctx, {"channel_id": 200, "status": "live"})
    assert result["planned"] is True
    ch.edit.assert_not_awaited()


async def test_voice_status_set_live():
    guild, ch = make_guild("voice")
    ctx = ctx_for(guild, dry_run=False)
    await channel_ops.voice_status_set(ctx, {"channel_id": 200, "status": "live"})
    ch.edit.assert_awaited_once_with(status="live", reason=None)


async def test_typing_live():
    guild, ch = make_guild()
    entered = {"value": False}

    @asynccontextmanager
    async def fake_typing():
        entered["value"] = True
        yield

    ch.typing = fake_typing
    ctx = ctx_for(guild, dry_run=False)
    result = await channel_ops.typing(ctx, {"channel_id": 200})
    assert entered["value"] is True
    assert result["channel_id"] == "200"


async def test_typing_dry_run():
    guild, ch = make_guild()
    ctx = ctx_for(guild, dry_run=True)
    result = await channel_ops.typing(ctx, {"channel_id": 200})
    assert result["planned"] is True
