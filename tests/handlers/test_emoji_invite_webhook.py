from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import emoji as emoji_ops
from discordctl.ops.handlers import invite as invite_ops
from discordctl.ops.handlers import webhook as webhook_ops
from discordctl.ops.registry import BusContext


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


async def test_emoji_list():
    em = SimpleNamespace(id=1, name="smile", animated=False)
    guild = SimpleNamespace(id=1, emojis=[em])
    result = await emoji_ops.list_emojis(ctx_for(guild, True), {})
    assert result[0]["name"] == "smile"


async def test_invite_create_dry_run():
    channel = SimpleNamespace(
        id=200, name="general", type=SimpleNamespace(name="text"), create_invite=AsyncMock()
    )
    guild = SimpleNamespace(
        id=1, channels=[channel], get_channel=lambda cid: channel if cid == 200 else None
    )
    result = await invite_ops.create(ctx_for(guild, True), {"channel_id": 200})
    assert result["planned"] is True
    channel.create_invite.assert_not_called()


async def test_webhook_create_live():
    wh = SimpleNamespace(id=5, name="hook", channel_id=200, url="http://x")
    channel = SimpleNamespace(
        id=200,
        name="general",
        type=SimpleNamespace(name="text"),
        create_webhook=AsyncMock(return_value=wh),
    )
    guild = SimpleNamespace(
        id=1, channels=[channel], get_channel=lambda cid: channel if cid == 200 else None
    )
    await webhook_ops.create(ctx_for(guild, False), {"channel_id": 200, "name": "hook"})
    channel.create_webhook.assert_awaited_once()
