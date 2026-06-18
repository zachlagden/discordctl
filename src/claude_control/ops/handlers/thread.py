from __future__ import annotations

from claude_control.ops import serialize
from claude_control.ops.lookup import resolve_channel, resolve_guild
from claude_control.ops.registry import HandlerError, op, plan


@op("thread.list_active")
async def list_active(ctx, args):
    guild = resolve_guild(ctx, args)
    return [serialize.thread_dict(t) for t in guild.threads]


@op("thread.list_archived")
async def list_archived(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    limit = int(args.get("limit", 50))
    out = []
    async for thread in channel.archived_threads(limit=limit):
        out.append(serialize.thread_dict(thread))
    return out


@op("thread.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    tid = int(args["thread_id"])
    thread = guild.get_thread(tid) if hasattr(guild, "get_thread") else None
    if thread is None:
        thread = guild.get_channel(tid)
    if thread is None:
        raise HandlerError(f"thread {tid} not found", code="not_found")
    return serialize.thread_dict(thread)


@op("thread.history")
async def history(ctx, args):
    guild = resolve_guild(ctx, args)
    tid = int(args["thread_id"])
    thread = guild.get_thread(tid) if hasattr(guild, "get_thread") else None
    if thread is None:
        thread = guild.get_channel(tid)
    if thread is None:
        raise HandlerError(f"thread {tid} not found", code="not_found")
    limit = int(args.get("limit", 50))
    out = []
    async for message in thread.history(limit=limit):
        out.append(serialize.message_dict(message))
    return out


@op("thread.create_forum_post", mutating=True)
async def create_forum_post(ctx, args):
    guild = resolve_guild(ctx, args)
    forum = resolve_channel(guild, args)
    name, content = args["name"], args["content"]
    if ctx.dry_run:
        return plan("thread.create_forum_post", channel_id=str(forum.id), name=name)
    created = await forum.create_thread(name=name, content=content)
    return serialize.thread_dict(created.thread)
