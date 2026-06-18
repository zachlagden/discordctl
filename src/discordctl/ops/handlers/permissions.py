from __future__ import annotations

import discord

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_channel, resolve_guild, resolve_member, resolve_role
from discordctl.ops.registry import HandlerError, op, plan


async def _resolve_target(guild, args):
    if args.get("role_id") is not None or args.get("role_name") is not None:
        return resolve_role(guild, args)
    if args.get("user_id") is not None:
        return await resolve_member(guild, args)
    raise HandlerError("role_id or user_id required", code="bad_args")


def _build_overwrite(allow, deny):
    mapping = {}
    for name in allow or []:
        mapping[name] = True
    for name in deny or []:
        mapping[name] = False
    try:
        return discord.PermissionOverwrite(**mapping)
    except (ValueError, TypeError) as exc:
        raise HandlerError(f"invalid permission name: {exc}", code="bad_args")


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
    target = await _resolve_target(guild, args)
    overwrite = _build_overwrite(args.get("allow"), args.get("deny"))
    if ctx.dry_run:
        return plan(
            "permissions.channel_overwrite_set",
            channel_id=str(channel.id),
            target_id=str(target.id),
            allow=args.get("allow"),
            deny=args.get("deny"),
        )
    await channel.set_permissions(target, overwrite=overwrite, reason=args.get("reason"))
    return {"channel_id": str(channel.id), "target_id": str(target.id)}


@op("permissions.channel_overwrite_clear", mutating=True)
async def channel_overwrite_clear(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    target = await _resolve_target(guild, args)
    if ctx.dry_run:
        return plan(
            "permissions.channel_overwrite_clear",
            channel_id=str(channel.id),
            target_id=str(target.id),
        )
    await channel.set_permissions(target, overwrite=None, reason=args.get("reason"))
    return {"cleared": str(target.id), "channel_id": str(channel.id)}
