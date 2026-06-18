from __future__ import annotations

from claude_control.ops import serialize
from claude_control.ops.lookup import resolve_channel, resolve_guild
from claude_control.ops.registry import HandlerError, op, plan


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
    content = args["content"]
    if ctx.dry_run:
        return plan("message.send", channel_id=str(channel.id), content=content)
    message = await channel.send(content=content)
    return serialize.message_dict(message)


@op("message.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("message.edit", channel_id=str(channel.id), message_id=str(args["message_id"]))
    message = await _fetch_message(channel, args["message_id"])
    await message.edit(content=args["content"])
    return serialize.message_dict(message)


@op("message.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("message.delete", channel_id=str(channel.id), message_id=str(args["message_id"]))
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
