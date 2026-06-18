from __future__ import annotations

import datetime

import discord

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_guild, resolve_member, resolve_user_id
from discordctl.ops.registry import HandlerError, op, plan


def _resolve_roles(guild, role_ids):
    roles = []
    for rid in role_ids:
        role = guild.get_role(int(rid))
        if role is None:
            raise HandlerError(f"role {rid} not found", code="not_found")
        roles.append(role)
    return roles


@op("member.list")
async def list_members(ctx, args):
    guild = resolve_guild(ctx, args)
    limit = int(args.get("limit", 100))
    return [serialize.member_dict(m) for m in list(guild.members)[:limit]]


@op("member.search")
async def search(ctx, args):
    guild = resolve_guild(ctx, args)
    q = str(args.get("query", "")).lower()
    out = [
        serialize.member_dict(m)
        for m in guild.members
        if q in m.name.lower() or q in (m.display_name or "").lower()
    ]
    return out[: int(args.get("limit", 25))]


@op("member.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    member = await resolve_member(guild, args)
    data = serialize.member_dict(member)
    status = getattr(member, "status", None)
    data["status"] = str(status) if status is not None else None
    activity = getattr(member, "activity", None)
    data["activity"] = getattr(activity, "name", None) if activity is not None else None
    return data


@op("member.ban", mutating=True)
async def ban(ctx, args):
    guild = resolve_guild(ctx, args)
    uid = resolve_user_id(args)
    if uid == guild.owner_id:
        raise HandlerError("refusing to act on guild owner", code="refused")
    if ctx.dry_run:
        return plan("ban", guild_id=str(guild.id), user_id=str(uid))
    await guild.ban(
        discord.Object(id=uid),
        reason=args.get("reason"),
        delete_message_seconds=int(args.get("delete_message_seconds", 0)),
    )
    return {"banned": str(uid)}


@op("member.unban", mutating=True)
async def unban(ctx, args):
    guild = resolve_guild(ctx, args)
    uid = resolve_user_id(args)
    if ctx.dry_run:
        return plan("unban", guild_id=str(guild.id), user_id=str(uid))
    await guild.unban(discord.Object(id=uid), reason=args.get("reason"))
    return {"unbanned": str(uid)}


@op("member.kick", mutating=True)
async def kick(ctx, args):
    guild = resolve_guild(ctx, args)
    member = await resolve_member(guild, args)
    if member.id == guild.owner_id:
        raise HandlerError("refusing to act on guild owner", code="refused")
    if ctx.dry_run:
        return plan("kick", guild_id=str(guild.id), user_id=str(member.id))
    await guild.kick(member, reason=args.get("reason"))
    return {"kicked": str(member.id)}


@op("member.timeout", mutating=True)
async def timeout(ctx, args):
    guild = resolve_guild(ctx, args)
    member = await resolve_member(guild, args)
    seconds = int(args["seconds"])
    if ctx.dry_run:
        return plan("timeout", user_id=str(member.id), seconds=seconds)
    await member.timeout(datetime.timedelta(seconds=seconds), reason=args.get("reason"))
    return {"timed_out": str(member.id), "seconds": seconds}


@op("member.untimeout", mutating=True)
async def untimeout(ctx, args):
    guild = resolve_guild(ctx, args)
    member = await resolve_member(guild, args)
    if ctx.dry_run:
        return plan("untimeout", user_id=str(member.id))
    await member.timeout(None, reason=args.get("reason"))
    return {"untimed_out": str(member.id)}


@op("member.nick", mutating=True)
async def nick(ctx, args):
    guild = resolve_guild(ctx, args)
    member = await resolve_member(guild, args)
    new_nick = args.get("nick")
    if ctx.dry_run:
        return plan("nick", user_id=str(member.id), nick=new_nick)
    await member.edit(nick=new_nick, reason=args.get("reason"))
    return {"member": str(member.id), "nick": new_nick}


@op("member.roles_add", mutating=True)
async def roles_add(ctx, args):
    guild = resolve_guild(ctx, args)
    member = await resolve_member(guild, args)
    roles = _resolve_roles(guild, args["role_ids"])
    if ctx.dry_run:
        return plan("roles_add", user_id=str(member.id), role_ids=[str(r.id) for r in roles])
    await member.add_roles(*roles, reason=args.get("reason"))
    return {"member": str(member.id), "added": [str(r.id) for r in roles]}


@op("member.roles_remove", mutating=True)
async def roles_remove(ctx, args):
    guild = resolve_guild(ctx, args)
    member = await resolve_member(guild, args)
    roles = _resolve_roles(guild, args["role_ids"])
    if ctx.dry_run:
        return plan("roles_remove", user_id=str(member.id), role_ids=[str(r.id) for r in roles])
    await member.remove_roles(*roles, reason=args.get("reason"))
    return {"member": str(member.id), "removed": [str(r.id) for r in roles]}


@op("member.roles_set", mutating=True)
async def roles_set(ctx, args):
    guild = resolve_guild(ctx, args)
    member = await resolve_member(guild, args)
    roles = _resolve_roles(guild, args["role_ids"])
    if ctx.dry_run:
        return plan("roles_set", user_id=str(member.id), role_ids=[str(r.id) for r in roles])
    await member.edit(roles=roles, reason=args.get("reason"))
    return {"member": str(member.id), "roles": [str(r.id) for r in roles]}


@op("member.voice_move", mutating=True)
async def voice_move(ctx, args):
    guild = resolve_guild(ctx, args)
    member = await resolve_member(guild, args)
    channel = guild.get_channel(int(args["channel_id"]))
    if channel is None:
        raise HandlerError("voice channel not found", code="not_found")
    if ctx.dry_run:
        return plan("voice_move", user_id=str(member.id), channel_id=str(channel.id))
    await member.move_to(channel, reason=args.get("reason"))
    return {"member": str(member.id), "moved_to": str(channel.id)}


@op("member.voice_disconnect", mutating=True)
async def voice_disconnect(ctx, args):
    guild = resolve_guild(ctx, args)
    member = await resolve_member(guild, args)
    if ctx.dry_run:
        return plan("voice_disconnect", user_id=str(member.id))
    await member.move_to(None, reason=args.get("reason"))
    return {"member": str(member.id), "disconnected": True}
