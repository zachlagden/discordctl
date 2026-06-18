from __future__ import annotations

import datetime

from discord.http import Route

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_guild
from discordctl.ops.registry import HandlerError, op, plan


@op("voice.state_get")
async def state_get(ctx, args):
    guild = resolve_guild(ctx, args)
    if args.get("user_id") is not None:
        uid = int(args["user_id"])
    else:
        uid = guild.me.id
    member = guild.get_member(uid)
    if member is None:
        try:
            member = await guild.fetch_member(uid)
        except Exception:
            raise HandlerError(f"member {uid} not found", code="not_found")
    state = getattr(member, "voice", None)
    data = serialize.voice_state_dict(state)
    data["user_id"] = str(uid)
    return data


@op("voice.state_self_set", mutating=True)
async def state_self_set(ctx, args):
    guild = resolve_guild(ctx, args)
    payload: dict = {}
    if args.get("channel_id") is not None:
        payload["channel_id"] = str(int(args["channel_id"]))
    if "suppress" in args:
        payload["suppress"] = bool(args["suppress"])
    if args.get("request_to_speak"):
        payload["request_to_speak_timestamp"] = datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()
    if not payload:
        raise HandlerError("one of channel_id/suppress/request_to_speak required", code="bad_args")
    if ctx.dry_run:
        return plan("voice.state_self_set", guild_id=str(guild.id), **payload)
    route = Route("PATCH", "/guilds/{guild_id}/voice-states/@me", guild_id=guild.id)
    await ctx.bot.http.request(route, json=payload)
    return {"guild_id": str(guild.id), "user_id": str(guild.me.id), "updated": payload}


@op("voice.state_set", mutating=True)
async def state_set(ctx, args):
    guild = resolve_guild(ctx, args)
    uid = int(args["user_id"])
    payload: dict = {}
    if args.get("channel_id") is not None:
        payload["channel_id"] = str(int(args["channel_id"]))
    if "suppress" in args:
        payload["suppress"] = bool(args["suppress"])
    if not payload:
        raise HandlerError("channel_id and/or suppress required", code="bad_args")
    if ctx.dry_run:
        return plan("voice.state_set", guild_id=str(guild.id), user_id=str(uid), **payload)
    route = Route(
        "PATCH",
        "/guilds/{guild_id}/voice-states/{user_id}",
        guild_id=guild.id,
        user_id=uid,
    )
    await ctx.bot.http.request(route, json=payload)
    return {"guild_id": str(guild.id), "user_id": str(uid), "updated": payload}
