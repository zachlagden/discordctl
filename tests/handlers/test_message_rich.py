import base64
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from discordctl.ops import message_build
from discordctl.ops.handlers import message as msg_ops
from discordctl.ops.handlers import user as user_ops
from discordctl.ops.registry import BusContext, HandlerError

BUTTON_ROW = [
    {
        "type": 1,
        "components": [{"type": 2, "style": 1, "label": "Click", "custom_id": "go"}],
    }
]


def _payload_from_params(params):
    if params.multipart:
        part = next(p for p in params.multipart if p["name"] == "payload_json")
        return json.loads(part["value"])
    return params.payload


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


def make_http_guild():
    guild, channel = make_guild()
    http = SimpleNamespace(
        send_message=AsyncMock(return_value={"id": "999"}),
        edit_message=AsyncMock(return_value={"id": "999"}),
    )
    sent = channel.send.return_value
    channel.fetch_message = AsyncMock(return_value=sent)
    bot = SimpleNamespace(get_guild=lambda gid: guild, http=http)
    return guild, channel, bot, http


def _assert_serializable_components(payload):
    serialized = json.dumps(payload)
    assert "components" in payload
    assert json.loads(serialized)["components"] == BUTTON_ROW


async def test_components_only_sends_via_http_with_components():
    guild, channel, bot, http = make_http_guild()
    await msg_ops.send(
        ctx_for(guild, False, bot=bot),
        {"channel_id": 200, "content": "hi", "components": BUTTON_ROW},
    )
    channel.send.assert_not_called()
    http.send_message.assert_awaited_once()
    params = http.send_message.await_args.kwargs["params"]
    payload = _payload_from_params(params)
    _assert_serializable_components(payload)
    assert payload["content"] == "hi"


async def test_components_with_files_keeps_components_in_payload_json():
    guild, channel, bot, http = make_http_guild()
    raw = base64.b64encode(b"bytes").decode()
    await msg_ops.send(
        ctx_for(guild, False, bot=bot),
        {
            "channel_id": 200,
            "content": "hi",
            "components": BUTTON_ROW,
            "files": [{"data": raw, "filename": "n.txt"}],
        },
    )
    params = http.send_message.await_args.kwargs["params"]
    assert params.multipart is not None
    assert params.files
    payload = _payload_from_params(params)
    _assert_serializable_components(payload)
    json.dumps(payload)


async def test_components_with_reference_serializes_reference_dict():
    guild, channel, bot, http = make_http_guild()
    await msg_ops.send(
        ctx_for(guild, False, bot=bot),
        {
            "channel_id": 200,
            "content": "reply",
            "components": BUTTON_ROW,
            "message_reference": {"message_id": 42},
        },
    )
    params = http.send_message.await_args.kwargs["params"]
    payload = _payload_from_params(params)
    json.dumps(payload)
    _assert_serializable_components(payload)
    assert payload["message_reference"]["message_id"] == 42
    assert payload["message_reference"]["channel_id"] == 200


async def test_components_with_stickers_uses_int_sticker_ids():
    guild, channel, bot, http = make_http_guild()
    await msg_ops.send(
        ctx_for(guild, False, bot=bot),
        {
            "channel_id": 200,
            "content": "stk",
            "components": BUTTON_ROW,
            "sticker_ids": [123, 456],
        },
    )
    params = http.send_message.await_args.kwargs["params"]
    payload = _payload_from_params(params)
    json.dumps(payload)
    _assert_serializable_components(payload)
    assert payload["sticker_ids"] == [123, 456]


async def test_components_with_suppress_and_silent_sets_flags():
    guild, channel, bot, http = make_http_guild()
    await msg_ops.send(
        ctx_for(guild, False, bot=bot),
        {
            "channel_id": 200,
            "content": "f",
            "components": BUTTON_ROW,
            "suppress_embeds": True,
            "silent": True,
        },
    )
    params = http.send_message.await_args.kwargs["params"]
    payload = _payload_from_params(params)
    json.dumps(payload)
    _assert_serializable_components(payload)
    flags = discord.MessageFlags._from_value(payload["flags"])
    assert flags.suppress_embeds is True
    assert flags.suppress_notifications is True


def make_edit_message():
    return SimpleNamespace(
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
        edit=AsyncMock(),
    )


async def test_edit_with_components_and_flags_via_http():
    guild, channel, bot, http = make_http_guild()
    message = make_edit_message()
    channel.fetch_message = AsyncMock(return_value=message)
    await msg_ops.edit(
        ctx_for(guild, False, bot=bot),
        {
            "channel_id": 200,
            "message_id": 999,
            "content": "edited",
            "components": BUTTON_ROW,
            "flags": {"suppress_embeds": True},
        },
    )
    message.edit.assert_not_called()
    http.edit_message.assert_awaited_once()
    params = http.edit_message.await_args.kwargs["params"]
    payload = _payload_from_params(params)
    json.dumps(payload)
    _assert_serializable_components(payload)
    assert payload["content"] == "edited"
    flags = discord.MessageFlags._from_value(payload["flags"])
    assert flags.suppress_embeds is True


async def test_edit_with_flags_no_components_maps_to_suppress():
    guild, channel, bot, http = make_http_guild()
    message = make_edit_message()
    channel.fetch_message = AsyncMock(return_value=message)
    await msg_ops.edit(
        ctx_for(guild, False, bot=bot),
        {
            "channel_id": 200,
            "message_id": 999,
            "content": "edited",
            "flags": {"suppress_embeds": True},
        },
    )
    http.edit_message.assert_not_called()
    message.edit.assert_awaited_once()
    edit_kwargs = message.edit.await_args.kwargs
    assert edit_kwargs["suppress"] is True
    assert "flags" not in edit_kwargs
    assert edit_kwargs["content"] == "edited"
