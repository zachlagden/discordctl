from __future__ import annotations

import base64
import io
import json
from datetime import timedelta
from typing import Any

import discord

from discordctl.ops.registry import HandlerError

_SEND_KEYS = frozenset(
    {
        "content",
        "embeds",
        "files",
        "allowed_mentions",
        "tts",
        "silent",
        "suppress_embeds",
        "stickers",
        "reference",
        "poll",
        "components",
    }
)

_EDIT_KEYS = frozenset(
    {
        "content",
        "embeds",
        "allowed_mentions",
        "components",
        "flags",
    }
)


def _build_embeds(raw: Any) -> list[discord.Embed]:
    if not isinstance(raw, list):
        raise HandlerError("embeds must be a list", code="bad_args")
    if len(raw) > 10:
        raise HandlerError("a message accepts at most 10 embeds", code="bad_args")
    return [discord.Embed.from_dict(e) for e in raw]


def _build_files(raw: Any) -> list[discord.File]:
    if not isinstance(raw, list):
        raise HandlerError("files must be a list", code="bad_args")
    files: list[discord.File] = []
    for f in raw:
        try:
            data = base64.b64decode(f["data"])
        except (KeyError, ValueError, TypeError) as exc:
            raise HandlerError(f"invalid file payload: {exc}", code="bad_args") from exc
        files.append(discord.File(io.BytesIO(data), filename=f.get("filename")))
    return files


def _build_reference(raw: Any, default_channel_id: int | None = None) -> discord.MessageReference:
    if not isinstance(raw, dict) or raw.get("message_id") is None:
        raise HandlerError("message_reference requires message_id", code="bad_args")
    if raw.get("channel_id") is not None:
        channel_id = int(raw["channel_id"])
    elif default_channel_id is not None:
        channel_id = int(default_channel_id)
    else:
        channel_id = 0
    return discord.MessageReference(
        message_id=int(raw["message_id"]),
        channel_id=channel_id,
        fail_if_not_exists=bool(raw.get("fail_if_not_exists", True)),
    )


def _build_poll(raw: Any) -> discord.Poll:
    if not isinstance(raw, dict):
        raise HandlerError("poll must be an object", code="bad_args")
    question = raw.get("question")
    if not question:
        raise HandlerError("poll requires a question", code="bad_args")
    hours = raw.get("duration_hours", raw.get("duration", 24))
    poll = discord.Poll(
        question=str(question),
        duration=timedelta(hours=float(hours)),
        multiple=bool(raw.get("multiple", False)),
    )
    for answer in raw.get("answers", []):
        if isinstance(answer, str):
            poll.add_answer(text=answer)
        else:
            poll.add_answer(text=str(answer["text"]), emoji=answer.get("emoji"))
    return poll


def build_message_kwargs(
    args: dict[str, Any], *, edit: bool = False, channel_id: int | None = None
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}

    if args.get("content") is not None:
        kwargs["content"] = str(args["content"])

    if args.get("embeds") is not None:
        kwargs["embeds"] = _build_embeds(args["embeds"])

    if args.get("allowed_mentions") is not None:
        kwargs["allowed_mentions"] = discord.AllowedMentions(**args["allowed_mentions"])

    if args.get("components") is not None:
        kwargs["components"] = args["components"]

    if edit:
        if args.get("flags") is not None:
            kwargs["flags"] = discord.MessageFlags(**args["flags"])
        return {k: v for k, v in kwargs.items() if k in _EDIT_KEYS}

    if args.get("files") is not None:
        kwargs["files"] = _build_files(args["files"])

    if args.get("tts") is not None:
        kwargs["tts"] = bool(args["tts"])

    if args.get("silent") is not None:
        kwargs["silent"] = bool(args["silent"])

    if args.get("suppress_embeds") is not None:
        kwargs["suppress_embeds"] = bool(args["suppress_embeds"])

    if args.get("sticker_ids") is not None:
        kwargs["stickers"] = [discord.Object(id=int(x)) for x in args["sticker_ids"]]

    reference = args.get("message_reference") or args.get("reply")
    if reference is not None:
        kwargs["reference"] = _build_reference(reference, channel_id)

    if args.get("poll") is not None:
        kwargs["poll"] = _build_poll(args["poll"])

    return {k: v for k, v in kwargs.items() if k in _SEND_KEYS}


def _inject_components(params: Any, components: Any, extra: dict[str, Any] | None = None) -> Any:
    from discord import http

    if params.multipart:
        payload_json = next(part for part in params.multipart if part["name"] == "payload_json")
        payload = json.loads(payload_json["value"])
        payload["components"] = components
        if extra:
            payload.update(extra)
        payload_json["value"] = http.utils._to_json(payload)
        return params
    payload = dict(params.payload or {})
    payload["components"] = components
    if extra:
        payload.update(extra)
    return params._replace(payload=payload)


def _params_with_components(kwargs: dict[str, Any], components: Any) -> Any:
    from discord import http

    skip = {"suppress_embeds", "silent", "reference"}
    param_kwargs = {k: v for k, v in kwargs.items() if k not in skip}
    if "reference" in kwargs:
        param_kwargs["message_reference"] = kwargs["reference"].to_message_reference_dict()
    if "stickers" in kwargs:
        param_kwargs["stickers"] = [o.id for o in kwargs["stickers"]]
    flags = param_kwargs.get("flags") or discord.MessageFlags()
    if kwargs.get("suppress_embeds"):
        flags.suppress_embeds = True
    if kwargs.get("silent"):
        flags.suppress_notifications = True
    if flags.value:
        param_kwargs["flags"] = flags
    params = http.handle_message_parameters(**param_kwargs)
    return _inject_components(params, components)


async def perform_send(ctx: Any, channel: Any, kwargs: dict[str, Any]) -> Any:
    components = kwargs.pop("components", None)
    if components is None:
        return await channel.send(**kwargs)
    params = _params_with_components(kwargs, components)
    data = await ctx.bot.http.send_message(channel.id, params=params)
    return await channel.fetch_message(int(data["id"]))


async def perform_edit(ctx: Any, message: Any, kwargs: dict[str, Any]) -> Any:
    components = kwargs.pop("components", None)
    flags = kwargs.pop("flags", None)
    if components is None:
        edit_kwargs = dict(kwargs)
        if flags is not None and flags.suppress_embeds:
            edit_kwargs["suppress"] = True
        await message.edit(**edit_kwargs)
        return message
    from discord import http

    extra: dict[str, Any] = {}
    if flags is not None:
        extra["flags"] = flags.value
    params = http.handle_message_parameters(**kwargs)
    params = _inject_components(params, components, extra)
    await ctx.bot.http.edit_message(message.channel.id, message.id, params=params)
    return message
