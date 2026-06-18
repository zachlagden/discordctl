from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discordctl.ops.handlers import message as msg_ops
from discordctl.ops.registry import BusContext, HandlerError


def make_message(message_id=999, reactions=None):
    return SimpleNamespace(
        id=message_id,
        channel=SimpleNamespace(id=200),
        author=SimpleNamespace(id=1, name="bot"),
        content="hi",
        pinned=False,
        created_at=None,
        reactions=reactions or [],
        remove_reaction=AsyncMock(),
        clear_reaction=AsyncMock(),
        clear_reactions=AsyncMock(),
        publish=AsyncMock(),
    )


async def _aiter(items):
    for item in items:
        yield item


def make_guild(message=None, pins=None):
    message = message or make_message()

    def users(limit=100):
        return _aiter([SimpleNamespace(id=5, name="alice", avatar=None)])

    channel = SimpleNamespace(
        id=200,
        name="general",
        type=SimpleNamespace(name="text"),
        fetch_message=AsyncMock(return_value=message),
        delete_messages=AsyncMock(),
        pins=lambda: _aiter(pins or []),
    )
    guild = SimpleNamespace(
        id=1, channels=[channel], get_channel=lambda cid: channel if cid == 200 else None
    )
    return guild, channel, message, users


def ctx_for(guild, dry_run, bot_user=None):
    return BusContext(
        bot=SimpleNamespace(
            get_guild=lambda gid: guild, user=bot_user or SimpleNamespace(id=1, name="bot")
        ),
        dry_run=dry_run,
        confirm=not dry_run,
        yes_really=False,
        actor="t",
        write_enabled=True,
        allowed_guild_ids=frozenset({1}),
        default_guild_id=1,
    )


async def test_get_returns_dict():
    guild, channel, message, _ = make_guild()
    result = await msg_ops.get(ctx_for(guild, True), {"channel_id": 200, "message_id": 999})
    assert result["id"] == "999"
    assert result["channel_id"] == "200"
    channel.fetch_message.assert_awaited_once_with(999)


async def test_reactions_list_returns_users():
    guild, channel, message, users = make_guild()
    reaction = SimpleNamespace(emoji="👍", users=users)
    message.reactions = [reaction]
    result = await msg_ops.reactions_list(
        ctx_for(guild, True), {"channel_id": 200, "message_id": 999, "emoji": "👍"}
    )
    assert result == [
        {"id": "5", "name": "alice", "global_name": None, "bot": False, "avatar": None}
    ]


async def test_reactions_list_no_match_returns_empty():
    guild, channel, message, _ = make_guild()
    message.reactions = []
    result = await msg_ops.reactions_list(
        ctx_for(guild, True), {"channel_id": 200, "message_id": 999, "emoji": "👍"}
    )
    assert result == []


async def test_reaction_remove_dry_run():
    guild, channel, message, _ = make_guild()
    result = await msg_ops.reaction_remove(
        ctx_for(guild, True), {"channel_id": 200, "message_id": 999, "emoji": "👍"}
    )
    assert result["planned"] is True
    message.remove_reaction.assert_not_called()


async def test_reaction_remove_live_own():
    guild, channel, message, _ = make_guild()
    bot_user = SimpleNamespace(id=1, name="bot")
    await msg_ops.reaction_remove(
        ctx_for(guild, False, bot_user=bot_user),
        {"channel_id": 200, "message_id": 999, "emoji": "👍"},
    )
    message.remove_reaction.assert_awaited_once_with("👍", bot_user)


async def test_reaction_remove_live_user_id():
    guild, channel, message, _ = make_guild()
    await msg_ops.reaction_remove(
        ctx_for(guild, False),
        {"channel_id": 200, "message_id": 999, "emoji": "👍", "user_id": 42},
    )
    message.remove_reaction.assert_awaited_once()
    call_emoji, call_target = message.remove_reaction.await_args.args
    assert call_emoji == "👍"
    assert call_target.id == 42


async def test_reactions_clear_all_live():
    guild, channel, message, _ = make_guild()
    await msg_ops.reactions_clear(ctx_for(guild, False), {"channel_id": 200, "message_id": 999})
    message.clear_reactions.assert_awaited_once()
    message.clear_reaction.assert_not_called()


async def test_reactions_clear_by_emoji_live():
    guild, channel, message, _ = make_guild()
    await msg_ops.reactions_clear(
        ctx_for(guild, False), {"channel_id": 200, "message_id": 999, "emoji": "👍"}
    )
    message.clear_reaction.assert_awaited_once_with("👍")
    message.clear_reactions.assert_not_called()


async def test_reactions_clear_dry_run():
    guild, channel, message, _ = make_guild()
    result = await msg_ops.reactions_clear(
        ctx_for(guild, True), {"channel_id": 200, "message_id": 999}
    )
    assert result["planned"] is True
    message.clear_reactions.assert_not_called()


async def test_pins_list_returns_messages():
    pins = [make_message(message_id=111), make_message(message_id=222)]
    guild, channel, _, _ = make_guild(pins=pins)
    result = await msg_ops.pins_list(ctx_for(guild, True), {"channel_id": 200})
    assert [m["id"] for m in result] == ["111", "222"]


async def test_crosspost_dry_run():
    guild, channel, message, _ = make_guild()
    result = await msg_ops.crosspost(ctx_for(guild, True), {"channel_id": 200, "message_id": 999})
    assert result["planned"] is True
    message.publish.assert_not_called()


async def test_crosspost_live():
    guild, channel, message, _ = make_guild()
    result = await msg_ops.crosspost(ctx_for(guild, False), {"channel_id": 200, "message_id": 999})
    message.publish.assert_awaited_once()
    assert result["id"] == "999"


async def test_bulk_delete_dry_run():
    guild, channel, _, _ = make_guild()
    result = await msg_ops.bulk_delete(
        ctx_for(guild, True), {"channel_id": 200, "message_ids": [1, 2, 3]}
    )
    assert result["planned"] is True
    assert result["count"] == 3
    channel.delete_messages.assert_not_called()


async def test_bulk_delete_live():
    guild, channel, _, _ = make_guild()
    result = await msg_ops.bulk_delete(
        ctx_for(guild, False), {"channel_id": 200, "message_ids": [10, 20]}
    )
    channel.delete_messages.assert_awaited_once()
    sent = channel.delete_messages.await_args.args[0]
    assert [o.id for o in sent] == [10, 20]
    assert result["deleted"] == 2


async def test_bulk_delete_too_few_raises():
    guild, channel, _, _ = make_guild()
    with pytest.raises(HandlerError) as exc:
        await msg_ops.bulk_delete(ctx_for(guild, False), {"channel_id": 200, "message_ids": [1]})
    assert exc.value.code == "bad_args"


async def test_bulk_delete_too_many_raises():
    guild, channel, _, _ = make_guild()
    with pytest.raises(HandlerError) as exc:
        await msg_ops.bulk_delete(
            ctx_for(guild, False), {"channel_id": 200, "message_ids": list(range(101))}
        )
    assert exc.value.code == "bad_args"
