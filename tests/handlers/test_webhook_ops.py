from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discordctl.ops.handlers import webhook as webhook_ops
from discordctl.ops.registry import BusContext


def make_message(mid=99):
    return SimpleNamespace(
        id=mid,
        channel=SimpleNamespace(id=200),
        author=SimpleNamespace(id=7, name="hook"),
        content="hi",
        pinned=False,
        created_at=None,
        embeds=[],
        attachments=[],
        components=[],
        poll=None,
        flags=SimpleNamespace(value=0),
    )


def make_webhook():
    return SimpleNamespace(
        id=5,
        name="hook",
        channel_id=200,
        url="http://x",
        send=AsyncMock(return_value=make_message()),
        fetch_message=AsyncMock(return_value=make_message()),
        edit_message=AsyncMock(return_value=make_message()),
        delete_message=AsyncMock(),
        edit=AsyncMock(),
    )


def ctx_for(guild, bot, dry_run):
    return BusContext(
        bot=bot,
        dry_run=dry_run,
        confirm=not dry_run,
        yes_really=False,
        actor="t",
        write_enabled=True,
        allowed_guild_ids=frozenset({1}),
        default_guild_id=1,
    )


def bot_for(guild, wh):
    return SimpleNamespace(
        get_guild=lambda gid: guild,
        fetch_webhook=AsyncMock(return_value=wh),
    )


def guild_for(webhooks=None):
    channel = SimpleNamespace(id=200, name="general")
    return SimpleNamespace(
        id=1,
        channels=[channel],
        get_channel=lambda cid: channel if cid == 200 else None,
        webhooks=AsyncMock(return_value=webhooks or []),
    )


async def test_execute_dry_run_does_not_send():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    result = await webhook_ops.execute(
        ctx_for(guild, bot, True), {"webhook_id": 5, "content": "hi"}
    )
    assert result["planned"] is True
    wh.send.assert_not_called()
    bot.fetch_webhook.assert_not_called()


async def test_execute_live_sends():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    result = await webhook_ops.execute(
        ctx_for(guild, bot, False),
        {"webhook_id": 5, "content": "hi", "username": "bob", "thread_id": 300},
    )
    wh.send.assert_awaited_once()
    kwargs = wh.send.await_args.kwargs
    assert kwargs["content"] == "hi"
    assert kwargs["username"] == "bob"
    assert kwargs["wait"] is True
    assert kwargs["thread"].id == 300
    assert result["id"] == "99"


async def test_execute_rejects_components():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    with pytest.raises(Exception):
        await webhook_ops.execute(
            ctx_for(guild, bot, False),
            {"webhook_id": 5, "components": [{"type": 1}]},
        )


async def test_message_get():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    result = await webhook_ops.message_get(
        ctx_for(guild, bot, True), {"webhook_id": 5, "message_id": 99}
    )
    wh.fetch_message.assert_awaited_once()
    assert result["id"] == "99"


async def test_message_edit_dry_run():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    result = await webhook_ops.message_edit(
        ctx_for(guild, bot, True), {"webhook_id": 5, "message_id": 99, "content": "x"}
    )
    assert result["planned"] is True
    wh.edit_message.assert_not_called()


async def test_message_edit_live():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    await webhook_ops.message_edit(
        ctx_for(guild, bot, False), {"webhook_id": 5, "message_id": 99, "content": "x"}
    )
    wh.edit_message.assert_awaited_once()
    assert wh.edit_message.await_args.kwargs["content"] == "x"


async def test_message_delete_dry_run():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    result = await webhook_ops.message_delete(
        ctx_for(guild, bot, True), {"webhook_id": 5, "message_id": 99}
    )
    assert result["planned"] is True
    wh.delete_message.assert_not_called()


async def test_message_delete_live():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    result = await webhook_ops.message_delete(
        ctx_for(guild, bot, False), {"webhook_id": 5, "message_id": 99}
    )
    wh.delete_message.assert_awaited_once()
    assert result["deleted"] == "99"


async def test_info():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    result = await webhook_ops.info(ctx_for(guild, bot, True), {"webhook_id": 5})
    assert result["id"] == "5"
    assert result["name"] == "hook"


async def test_guild_list():
    wh = make_webhook()
    guild = guild_for(webhooks=[wh])
    bot = bot_for(guild, wh)
    result = await webhook_ops.guild_list(ctx_for(guild, bot, True), {})
    assert result[0]["id"] == "5"


async def test_edit_dry_run():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    result = await webhook_ops.edit(ctx_for(guild, bot, True), {"webhook_id": 5, "name": "new"})
    assert result["planned"] is True
    bot.fetch_webhook.assert_not_called()


async def test_edit_live():
    wh = make_webhook()
    guild = guild_for()
    bot = bot_for(guild, wh)
    wh.edit = AsyncMock(return_value=wh)
    await webhook_ops.edit(
        ctx_for(guild, bot, False), {"webhook_id": 5, "name": "new", "channel_id": 200}
    )
    wh.edit.assert_awaited_once()
    kwargs = wh.edit.await_args.kwargs
    assert kwargs["name"] == "new"
    assert kwargs["channel"].id == 200
