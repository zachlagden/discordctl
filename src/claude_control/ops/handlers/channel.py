from __future__ import annotations

from claude_control.ops import serialize
from claude_control.ops.lookup import resolve_channel, resolve_guild
from claude_control.ops.registry import HandlerError, op, plan

_EDITABLE = ("name", "topic", "nsfw", "slowmode_delay", "position")
_CREATORS = {
    "text": "create_text_channel",
    "voice": "create_voice_channel",
    "forum": "create_forum",
    "stage": "create_stage_channel",
    "category": "create_category",
}


@op("channel.list")
async def list_channels(ctx, args):
    guild = resolve_guild(ctx, args)
    return [serialize.channel_dict(c) for c in guild.channels]


@op("channel.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    return serialize.channel_dict(resolve_channel(guild, args))


@op("channel.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    ctype = str(args.get("type", "text"))
    method_name = _CREATORS.get(ctype)
    if method_name is None:
        raise HandlerError(f"unsupported channel type {ctype!r}", code="bad_args")
    name = args["name"]
    if ctx.dry_run:
        return plan("channel.create", type=ctype, name=name)
    kwargs = {}
    if args.get("category_id") is not None:
        kwargs["category"] = guild.get_channel(int(args["category_id"]))
    for field in ("topic", "nsfw"):
        if args.get(field) is not None:
            kwargs[field] = args[field]
    channel = await getattr(guild, method_name)(name, reason=args.get("reason"), **kwargs)
    return serialize.channel_dict(channel)


@op("channel.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    fields = {k: args[k] for k in _EDITABLE if k in args}
    if ctx.dry_run:
        return plan("channel.edit", channel_id=str(channel.id), fields=fields)
    await channel.edit(reason=args.get("reason"), **fields)
    return serialize.channel_dict(channel)


@op("channel.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("channel.delete", channel_id=str(channel.id), name=channel.name)
    await channel.delete(reason=args.get("reason"))
    return {"deleted": str(channel.id)}


@op("channel.move", mutating=True)
async def move(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    position = int(args["position"])
    if ctx.dry_run:
        return plan("channel.move", channel_id=str(channel.id), position=position)
    await channel.edit(position=position, reason=args.get("reason"))
    return serialize.channel_dict(channel)


@op("channel.clone", mutating=True)
async def clone(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("channel.clone", channel_id=str(channel.id))
    new = await channel.clone(name=args.get("name"), reason=args.get("reason"))
    return serialize.channel_dict(new)


@op("channel.sync", mutating=True)
async def sync(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("channel.sync", channel_id=str(channel.id))
    await channel.edit(sync_permissions=True, reason=args.get("reason"))
    return {"synced": str(channel.id)}
