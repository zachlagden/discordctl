from __future__ import annotations

from claude_control.ops import serialize
from claude_control.ops.lookup import resolve_channel, resolve_guild
from claude_control.ops.registry import HandlerError, op, plan


@op("invite.list")
async def list_invites(ctx, args):
    guild = resolve_guild(ctx, args)
    invites = await guild.invites()
    return [serialize.invite_dict(i) for i in invites]


@op("invite.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("invite.create", channel_id=str(channel.id))
    invite = await channel.create_invite(
        max_age=int(args.get("max_age", 0)), max_uses=int(args.get("max_uses", 0)),
        reason=args.get("reason"),
    )
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
