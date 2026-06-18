from __future__ import annotations

import base64

import discord

import discordctl
from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_guild
from discordctl.ops.registry import REGISTRY, HandlerError, op, plan


@op("bot.ping")
async def ping(ctx, args):
    return {"latency_ms": round(ctx.bot.latency * 1000)}


@op("bot.version")
async def version(ctx, args):
    return {"version": discordctl.__version__}


@op("bot.guilds")
async def guilds(ctx, args):
    return [
        {"id": str(g.id), "name": g.name, "member_count": getattr(g, "member_count", None)}
        for g in ctx.bot.guilds
    ]


@op("bot.stats")
async def stats(ctx, args):
    return {"guilds": len(list(ctx.bot.guilds)), "ops": len(REGISTRY.ops())}


def _build_activity(activity_type, name, url):
    if activity_type == "custom":
        return discord.CustomActivity(name=name)
    if activity_type == "playing":
        return discord.Game(name=name)
    if activity_type == "streaming":
        return discord.Streaming(name=name, url=url)
    if activity_type == "listening":
        return discord.Activity(type=discord.ActivityType.listening, name=name)
    if activity_type == "watching":
        return discord.Activity(type=discord.ActivityType.watching, name=name)
    if activity_type == "competing":
        return discord.Activity(type=discord.ActivityType.competing, name=name)
    raise HandlerError(f"unknown presence type {activity_type!r}", code="bad_args")


@op("bot.presence_set", mutating=True)
async def presence_set(ctx, args):
    activity_type = args.get("type")
    name = args.get("name")
    status_name = args.get("status", "online")
    url = args.get("url")
    if activity_type not in {
        "playing",
        "streaming",
        "listening",
        "watching",
        "competing",
        "custom",
    }:
        raise HandlerError(f"unknown presence type {activity_type!r}", code="bad_args")
    if status_name not in {"online", "idle", "dnd", "invisible"}:
        raise HandlerError(f"unknown status {status_name!r}", code="bad_args")
    state = {"type": activity_type, "name": name, "status": status_name, "url": url}
    if ctx.dry_run:
        return plan("bot.presence_set", **state)
    activity = _build_activity(activity_type, name, url)
    status = discord.Status(status_name)
    await ctx.bot.change_presence(activity=activity, status=status)
    ctx.bot.presence_state = state
    return state


@op("bot.presence_clear", mutating=True)
async def presence_clear(ctx, args):
    if ctx.dry_run:
        return plan("bot.presence_clear")
    await ctx.bot.change_presence(activity=None, status=discord.Status.online)
    ctx.bot.presence_state = None
    return {"presence": None}


@op("bot.presence_get")
async def presence_get(ctx, args):
    state = getattr(ctx.bot, "presence_state", None)
    if state is None:
        return {"presence": None}
    return state


@op("bot.profile_edit", mutating=True)
async def profile_edit(ctx, args):
    kwargs = {}
    if args.get("username") is not None:
        kwargs["username"] = args["username"]
    if args.get("avatar_b64") is not None:
        kwargs["avatar"] = base64.b64decode(args["avatar_b64"])
    if ctx.dry_run:
        return plan("bot.profile_edit", fields=sorted(kwargs))
    await ctx.bot.user.edit(**kwargs)
    return serialize.user_dict(ctx.bot.user)


@op("bot.leave_guild", mutating=True)
async def leave_guild(ctx, args):
    guild = resolve_guild(ctx, args)
    if not ctx.yes_really:
        raise HandlerError(
            "leaving a guild is destructive; pass --yes-really", code="needs_yes_really"
        )
    if ctx.dry_run:
        return plan("bot.leave_guild", guild_id=str(guild.id), name=guild.name)
    await guild.leave()
    return {"left": str(guild.id)}


@op("bot.gateway")
async def gateway(ctx, args):
    try:
        shards, url, session_start_limit = await ctx.bot.http.get_bot_gateway()
    except Exception:
        return {
            "latency_ms": round(ctx.bot.latency * 1000),
            "shard_count": ctx.bot.shard_count,
        }
    return {
        "url": url,
        "shards": shards,
        "session_start_limit": session_start_limit,
    }
