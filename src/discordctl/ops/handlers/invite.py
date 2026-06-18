from __future__ import annotations

import discord

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_channel, resolve_guild
from discordctl.ops.registry import HandlerError, op, plan

_TARGET_TYPES = {
    "stream": discord.InviteTarget.stream,
    "embedded_application": discord.InviteTarget.embedded_application,
}


@op("invite.list")
async def list_invites(ctx, args):
    guild = resolve_guild(ctx, args)
    invites = await guild.invites()
    return [serialize.invite_dict(i) for i in invites]


@op("invite.list_guild")
async def list_guild(ctx, args):
    guild = resolve_guild(ctx, args)
    invites = await guild.invites()
    return [serialize.invite_dict(i) for i in invites]


@op("invite.info")
async def info(ctx, args):
    code = str(args["code"])
    with_counts = bool(args.get("with_counts", True))
    with_expiration = bool(args.get("with_expiration", True))
    try:
        invite = await ctx.bot.fetch_invite(
            code, with_counts=with_counts, with_expiration=with_expiration
        )
    except discord.NotFound:
        raise HandlerError(f"invite {code!r} not found", code="not_found")
    return serialize.invite_dict(invite)


@op("invite.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)

    kwargs: dict = {}
    if "max_age" in args:
        kwargs["max_age"] = int(args["max_age"])
    if "max_uses" in args:
        kwargs["max_uses"] = int(args["max_uses"])
    if "temporary" in args:
        kwargs["temporary"] = bool(args["temporary"])
    if "unique" in args:
        kwargs["unique"] = bool(args["unique"])
    if args.get("reason") is not None:
        kwargs["reason"] = args["reason"]

    target_type = args.get("target_type")
    if target_type is not None:
        if target_type not in _TARGET_TYPES:
            raise HandlerError(
                "target_type must be 'stream' or 'embedded_application'", code="bad_args"
            )
        kwargs["target_type"] = _TARGET_TYPES[target_type]

    if args.get("target_user_id") is not None:
        target_user = guild.get_member(int(args["target_user_id"]))
        if target_user is None:
            raise HandlerError("target_user_id not found in guild", code="not_found")
        kwargs["target_user"] = target_user

    if args.get("target_application_id") is not None:
        kwargs["target_application_id"] = int(args["target_application_id"])

    if ctx.dry_run:
        return plan("invite.create", channel_id=str(channel.id))
    invite = await channel.create_invite(**kwargs)
    return serialize.invite_dict(invite)


@op("invite.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    code = str(args["code"])
    invites = await guild.invites()
    match = [i for i in invites if i.code == code]
    if not match:
        raise HandlerError(f"invite {code!r} not found", code="not_found")
    if ctx.dry_run:
        return plan("invite.delete", code=code)
    await match[0].delete(reason=args.get("reason"))
    return {"deleted": code}
