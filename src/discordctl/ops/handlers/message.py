from __future__ import annotations

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_channel, resolve_guild
from discordctl.ops.message_build import build_message_kwargs, perform_edit, perform_send
from discordctl.ops.registry import HandlerError, op, plan


async def _fetch_message(channel, message_id):
    return await channel.fetch_message(int(message_id))


@op("message.history")
async def history(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    limit = int(args.get("limit", 50))
    out = []
    async for message in channel.history(limit=limit):
        out.append(serialize.message_dict(message))
    return out


@op("message.search")
async def search(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    needle = str(args.get("query", "")).lower()
    limit = int(args.get("limit", 200))
    out = []
    async for message in channel.history(limit=limit):
        if needle in (message.content or "").lower():
            out.append(serialize.message_dict(message))
    return out


@op("message.send", mutating=True)
async def send(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    kwargs = build_message_kwargs(args, channel_id=channel.id)
    if ctx.dry_run:
        return plan(
            "message.send",
            channel_id=str(channel.id),
            has_embeds=bool(kwargs.get("embeds")),
            has_components=bool(kwargs.get("components")),
            has_files=bool(kwargs.get("files")),
        )
    message = await perform_send(ctx, channel, kwargs)
    return serialize.message_dict(message)


@op("message.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    kwargs = build_message_kwargs(args, edit=True)
    if ctx.dry_run:
        return plan(
            "message.edit",
            channel_id=str(channel.id),
            message_id=str(args["message_id"]),
            has_embeds=bool(kwargs.get("embeds")),
            has_components=bool(kwargs.get("components")),
        )
    message = await _fetch_message(channel, args["message_id"])
    message = await perform_edit(ctx, message, kwargs)
    return serialize.message_dict(message)


@op("message.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan(
            "message.delete", channel_id=str(channel.id), message_id=str(args["message_id"])
        )
    message = await _fetch_message(channel, args["message_id"])
    await message.delete()
    return {"deleted": str(args["message_id"])}


@op("message.purge", mutating=True)
async def purge(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    limit = int(args["limit"])
    if limit > 100 and not ctx.yes_really:
        raise HandlerError("purge of >100 messages requires yes_really", code="needs_yes_really")
    if ctx.dry_run:
        return plan("message.purge", channel_id=str(channel.id), limit=limit)
    deleted = await channel.purge(limit=limit)
    return {"purged": len(deleted), "channel_id": str(channel.id)}


@op("message.pin", mutating=True)
async def pin(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("message.pin", message_id=str(args["message_id"]))
    message = await _fetch_message(channel, args["message_id"])
    await message.pin(reason=args.get("reason"))
    return {"pinned": str(args["message_id"])}


@op("message.unpin", mutating=True)
async def unpin(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("message.unpin", message_id=str(args["message_id"]))
    message = await _fetch_message(channel, args["message_id"])
    await message.unpin(reason=args.get("reason"))
    return {"unpinned": str(args["message_id"])}


@op("message.react", mutating=True)
async def react(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    emoji = args["emoji"]
    if ctx.dry_run:
        return plan("message.react", message_id=str(args["message_id"]), emoji=emoji)
    message = await _fetch_message(channel, args["message_id"])
    await message.add_reaction(emoji)
    return {"reacted": str(args["message_id"]), "emoji": emoji}


@op("poll.end", mutating=True)
async def poll_end(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("poll.end", channel_id=str(channel.id), message_id=str(args["message_id"]))
    message = await _fetch_message(channel, args["message_id"])
    if getattr(message, "poll", None) is None:
        raise HandlerError("message has no poll", code="bad_args")
    ended = await message.end_poll()
    return serialize.message_dict(ended)


@op("poll.voters")
async def poll_voters(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    message = await _fetch_message(channel, args["message_id"])
    poll = getattr(message, "poll", None)
    if poll is None:
        raise HandlerError("message has no poll", code="bad_args")
    answer = poll.get_answer(int(args["answer_id"]))
    if answer is None:
        raise HandlerError(f"answer {args['answer_id']} not found", code="not_found")
    out = []
    async for user in answer.voters():
        out.append(serialize.user_dict(user))
    return out
