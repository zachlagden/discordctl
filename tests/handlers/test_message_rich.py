import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from discordctl.ops import message_build
from discordctl.ops.handlers import message as msg_ops
from discordctl.ops.handlers import user as user_ops
from discordctl.ops.registry import BusContext, HandlerError


def test_build_embeds_from_dict():
    kwargs = message_build.build_message_kwargs(
        {"embeds": [{"title": "Hello", "description": "World"}]}
    )
    assert len(kwargs["embeds"]) == 1
    assert isinstance(kwargs["embeds"][0], discord.Embed)
    assert kwargs["embeds"][0].title == "Hello"


def test_build_embeds_over_10_raises_bad_args():
    with pytest.raises(HandlerError) as exc:
        message_build.build_message_kwargs({"embeds": [{"title": str(i)} for i in range(11)]})
    assert exc.value.code == "bad_args"


def test_build_files_base64_decode():
    raw = base64.b64encode(b"file-bytes").decode()
    kwargs = message_build.build_message_kwargs({"files": [{"data": raw, "filename": "note.txt"}]})
    assert len(kwargs["files"]) == 1
    assert kwargs["files"][0].filename == "note.txt"


def test_build_allowed_mentions():
    kwargs = message_build.build_message_kwargs(
        {"content": "hi", "allowed_mentions": {"everyone": False, "users": True}}
    )
    assert isinstance(kwargs["allowed_mentions"], discord.AllowedMentions)
    assert kwargs["allowed_mentions"].everyone is False


def test_build_reply_reference():
    kwargs = message_build.build_message_kwargs(
        {"message_reference": {"message_id": 42, "channel_id": 7, "fail_if_not_exists": False}}
    )
    ref = kwargs["reference"]
    assert isinstance(ref, discord.MessageReference)
    assert ref.message_id == 42
    assert ref.fail_if_not_exists is False


def test_build_poll():
    kwargs = message_build.build_message_kwargs(
        {
            "poll": {
                "question": "Best color?",
                "duration_hours": 12,
                "multiple": True,
                "answers": [{"text": "Red"}, {"text": "Blue", "emoji": "\U0001f535"}],
            }
        }
    )
    poll = kwargs["poll"]
    assert isinstance(poll, discord.Poll)
    assert poll.question == "Best color?"
    assert len(poll.answers) == 2


def test_build_flags_edit_only():
    kwargs = message_build.build_message_kwargs({"flags": {"suppress_embeds": True}}, edit=True)
    assert isinstance(kwargs["flags"], discord.MessageFlags)
    assert kwargs["flags"].suppress_embeds is True


def test_edit_drops_send_only_keys():
    kwargs = message_build.build_message_kwargs(
        {"content": "hi", "files": [], "poll": {"question": "q", "answers": []}}, edit=True
    )
    assert "files" not in kwargs
    assert "poll" not in kwargs
    assert kwargs["content"] == "hi"


def test_build_silent_and_stickers_send():
    kwargs = message_build.build_message_kwargs(
        {"content": "hi", "silent": True, "sticker_ids": [123, 456]}
    )
    assert kwargs["silent"] is True
    assert len(kwargs["stickers"]) == 2


def make_guild():
    sent = SimpleNamespace(
        id=999,
        channel=SimpleNamespace(id=200),
        author=SimpleNamespace(id=1, name="bot"),
        content="hi",
        pinned=False,
        created_at=None,
        embeds=[],
        attachments=[],
        components=None,
        poll=None,
        flags=SimpleNamespace(value=0),
    )
    channel = SimpleNamespace(
        id=200,
        name="general",
        type=SimpleNamespace(name="text"),
        send=AsyncMock(return_value=sent),
    )
    guild = SimpleNamespace(
        id=1, channels=[channel], get_channel=lambda cid: channel if cid == 200 else None
    )
    return guild, channel


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


async def test_send_dry_run_does_not_call_send():
    guild, channel = make_guild()
    result = await msg_ops.send(
        ctx_for(guild, True),
        {"channel_id": 200, "embeds": [{"title": "x"}]},
    )
    assert result["planned"] is True
    assert result["has_embeds"] is True
    channel.send.assert_not_called()


async def test_send_live_embed_and_button_calls_send_once():
    guild, channel = make_guild()
    args = {
        "channel_id": 200,
        "content": "hi",
        "embeds": [{"title": "Hello"}],
        "allowed_mentions": {"everyone": False},
    }
    await msg_ops.send(ctx_for(guild, False), args)
    channel.send.assert_awaited_once()
    call_kwargs = channel.send.await_args.kwargs
    assert isinstance(call_kwargs["embeds"][0], discord.Embed)


async def test_dm_send_dry_run_does_not_fetch_user():
    guild, _ = make_guild()
    fetch_user = AsyncMock()
    bot = SimpleNamespace(get_guild=lambda gid: guild, fetch_user=fetch_user)
    result = await user_ops.dm_send(
        ctx_for(guild, True, bot=bot), {"user_id": 555, "content": "yo"}
    )
    assert result["planned"] is True
    fetch_user.assert_not_called()


async def test_dm_send_live_opens_dm_and_sends():
    guild, _ = make_guild()
    dm_sent = SimpleNamespace(
        id=1,
        channel=SimpleNamespace(id=10),
        author=SimpleNamespace(id=1, name="bot"),
        content="yo",
        pinned=False,
        created_at=None,
        embeds=[],
        attachments=[],
        components=None,
        poll=None,
        flags=SimpleNamespace(value=0),
    )
    dm = SimpleNamespace(send=AsyncMock(return_value=dm_sent))
    user = SimpleNamespace(create_dm=AsyncMock(return_value=dm))
    bot = SimpleNamespace(get_guild=lambda gid: guild, fetch_user=AsyncMock(return_value=user))
    await user_ops.dm_send(ctx_for(guild, False, bot=bot), {"user_id": 555, "content": "yo"})
    user.create_dm.assert_awaited_once()
    dm.send.assert_awaited_once()
