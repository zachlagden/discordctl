from __future__ import annotations

import discord

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_channel, resolve_guild
from discordctl.ops.registry import HandlerError, op, plan

_PRIVACY_LEVELS = {
    "guild_only": discord.PrivacyLevel.guild_only,
}


def _privacy(args, key="privacy_level"):
    value = str(args.get(key, "guild_only"))
    if value not in _PRIVACY_LEVELS:
        raise HandlerError(f"unknown privacy_level {value!r}", code="bad_args")
    return _PRIVACY_LEVELS[value]


async def _resolve_instance(channel):
    instance = getattr(channel, "instance", None)
    if instance is not None:
        return instance
    try:
        return await channel.fetch_instance()
    except discord.NotFound:
        raise HandlerError(f"no stage instance for channel {channel.id}", code="not_found")


@op("stage.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    topic = args["topic"]
    privacy = _privacy(args)
    if ctx.dry_run:
        return plan("stage.create", channel_id=str(channel.id), topic=topic)
    kwargs = {
        "topic": topic,
        "privacy_level": privacy,
        "send_start_notification": bool(args.get("send_start_notification", False)),
        "reason": args.get("reason"),
    }
    if args.get("scheduled_event_id") is not None:
        kwargs["scheduled_event"] = discord.Object(id=int(args["scheduled_event_id"]))
    instance = await channel.create_instance(**kwargs)
    return serialize.stage_dict(instance)


@op("stage.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    return serialize.stage_dict(await _resolve_instance(channel))


@op("stage.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    instance = await _resolve_instance(channel)
    fields = {}
    if args.get("topic") is not None:
        fields["topic"] = args["topic"]
    if args.get("privacy_level") is not None:
        fields["privacy_level"] = _privacy(args)
    if ctx.dry_run:
        return plan("stage.edit", channel_id=str(channel.id), fields=sorted(fields))
    await instance.edit(reason=args.get("reason"), **fields)
    return serialize.stage_dict(await _resolve_instance(channel))


@op("stage.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    instance = await _resolve_instance(channel)
    if ctx.dry_run:
        return plan("stage.delete", channel_id=str(channel.id))
    await instance.delete(reason=args.get("reason"))
    return {"channel_id": str(channel.id), "deleted": True}
