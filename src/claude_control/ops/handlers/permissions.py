from __future__ import annotations

import discord

from claude_control.ops import serialize
from claude_control.ops.lookup import resolve_channel, resolve_guild, resolve_member, resolve_role
from claude_control.ops.registry import HandlerError, op, plan


def _resolve_target(guild, channel, args):
    if args.get("role_id") is not None or args.get("role_name") is not None:
        return resolve_role(guild, args)
    if args.get("user_id") is not None:
        return guild.get_member(int(args["user_id"]))
    raise HandlerError("role_id or user_id required", code="bad_args")


def _build_overwrite(allow, deny):
    mapping = {}
    for name in allow or []:
        mapping[name] = True
    for name in deny or []:
        mapping[name] = False
    return discord.PermissionOverwrite(**mapping)


@op("permissions.channel_overwrites")
async def channel_overwrites(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    return [serialize.overwrite_dict(t, o) for t, o in channel.overwrites.items()]


@op("permissions.resolve_member")
async def resolve_member_perms(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    member = await resolve_member(guild, args)
    perms = channel.permissions_for(member)
    return {name: value for name, value in perms}


@op("permissions.resolve_role")
async def resolve_role_perms(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    role = resolve_role(guild, args)
    perms = channel.permissions_for(role)
    return {name: value for name, value in perms}


@op("permissions.channel_overwrite_set", mutating=True)
async def channel_overwrite_set(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    target = _resolve_target(guild, channel, args)
    overwrite = _build_overwrite(args.get("allow"), args.get("deny"))
    if ctx.dry_run:
        return plan("permissions.channel_overwrite_set", channel_id=str(channel.id),
                    target_id=str(target.id), allow=args.get("allow"), deny=args.get("deny"))
    await channel.set_permissions(target, overwrite=overwrite, reason=args.get("reason"))
    return {"channel_id": str(channel.id), "target_id": str(target.id)}


@op("permissions.channel_overwrite_clear", mutating=True)
async def channel_overwrite_clear(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    target = _resolve_target(guild, channel, args)
    if ctx.dry_run:
        return plan("permissions.channel_overwrite_clear", channel_id=str(channel.id),
                    target_id=str(target.id))
    await channel.set_permissions(target, overwrite=None, reason=args.get("reason"))
    return {"cleared": str(target.id), "channel_id": str(channel.id)}
