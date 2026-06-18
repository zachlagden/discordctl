from __future__ import annotations

import discord

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_channel, resolve_guild, resolve_user_id
from discordctl.ops.registry import HandlerError, op, plan

_THREAD_TYPES = {
    "public": discord.ChannelType.public_thread,
    "private": discord.ChannelType.private_thread,
}

_EDIT_FIELDS = (
    "name",
    "archived",
    "locked",
    "auto_archive_duration",
    "slowmode_delay",
    "invitable",
)


def _resolve_thread(guild, args):
    tid = int(args["thread_id"])
    thread = guild.get_thread(tid) if hasattr(guild, "get_thread") else None
    if thread is None:
        thread = guild.get_channel(tid)
    if thread is None:
        raise HandlerError(f"thread {tid} not found", code="not_found")
    return thread


@op("thread.list_active")
async def list_active(ctx, args):
    guild = resolve_guild(ctx, args)
    return [serialize.thread_dict(t) for t in guild.threads]


@op("thread.list_archived")
async def list_archived(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    limit = int(args.get("limit", 50))
    kind = str(args.get("type", "public"))
    if kind == "public":
        iterator = channel.archived_threads(limit=limit)
    elif kind == "private":
        iterator = channel.archived_threads(limit=limit, private=True)
    elif kind == "joined":
        iterator = channel.archived_threads(limit=limit, private=True, joined=True)
    else:
        raise HandlerError(f"unknown archived thread type {kind!r}", code="bad_args")
    out = []
    async for thread in iterator:
        out.append(serialize.thread_dict(thread))
    return out


@op("thread.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    return serialize.thread_dict(_resolve_thread(guild, args))


@op("thread.history")
async def history(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
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


@op("thread.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    name = args["name"]
    kind = str(args.get("type", "public"))
    if kind not in _THREAD_TYPES:
        raise HandlerError(f"unknown thread type {kind!r}", code="bad_args")
    if ctx.dry_run:
        return plan("thread.create", channel_id=str(channel.id), name=name, type=kind)
    kwargs = {"name": name, "type": _THREAD_TYPES[kind]}
    if args.get("auto_archive_duration") is not None:
        kwargs["auto_archive_duration"] = int(args["auto_archive_duration"])
    if args.get("invitable") is not None:
        kwargs["invitable"] = bool(args["invitable"])
    if args.get("slowmode_delay") is not None:
        kwargs["slowmode_delay"] = int(args["slowmode_delay"])
    thread = await channel.create_thread(**kwargs)
    return serialize.thread_dict(thread)


@op("thread.create_from_message", mutating=True)
async def create_from_message(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    name = args["name"]
    message_id = int(args["message_id"])
    if ctx.dry_run:
        return plan(
            "thread.create_from_message",
            channel_id=str(channel.id),
            message_id=str(message_id),
            name=name,
        )
    message = await channel.fetch_message(message_id)
    kwargs = {"name": name}
    if args.get("auto_archive_duration") is not None:
        kwargs["auto_archive_duration"] = int(args["auto_archive_duration"])
    thread = await message.create_thread(**kwargs)
    return serialize.thread_dict(thread)


@op("thread.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
    fields = {}
    for key in _EDIT_FIELDS:
        if args.get(key) is not None:
            fields[key] = args[key]
    if args.get("applied_tags") is not None:
        fields["applied_tags"] = [discord.Object(id=int(t)) for t in args["applied_tags"]]
    if ctx.dry_run:
        return plan("thread.edit", thread_id=str(thread.id), fields=sorted(fields))
    await thread.edit(reason=args.get("reason"), **fields)
    return serialize.thread_dict(thread)


@op("thread.archive", mutating=True)
async def archive(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
    if ctx.dry_run:
        return plan("thread.archive", thread_id=str(thread.id))
    await thread.edit(archived=True, reason=args.get("reason"))
    return serialize.thread_dict(thread)


@op("thread.lock", mutating=True)
async def lock(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
    if ctx.dry_run:
        return plan("thread.lock", thread_id=str(thread.id))
    await thread.edit(locked=True, reason=args.get("reason"))
    return serialize.thread_dict(thread)


@op("thread.join", mutating=True)
async def join(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
    if ctx.dry_run:
        return plan("thread.join", thread_id=str(thread.id))
    await thread.join()
    return serialize.thread_dict(thread)


@op("thread.leave", mutating=True)
async def leave(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
    if ctx.dry_run:
        return plan("thread.leave", thread_id=str(thread.id))
    await thread.leave()
    return serialize.thread_dict(thread)


@op("thread.member_add", mutating=True)
async def member_add(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
    user_id = resolve_user_id(args)
    if ctx.dry_run:
        return plan("thread.member_add", thread_id=str(thread.id), user_id=str(user_id))
    await thread.add_user(discord.Object(id=user_id))
    return {"thread_id": str(thread.id), "user_id": str(user_id), "added": True}


@op("thread.member_remove", mutating=True)
async def member_remove(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
    user_id = resolve_user_id(args)
    if ctx.dry_run:
        return plan("thread.member_remove", thread_id=str(thread.id), user_id=str(user_id))
    await thread.remove_user(discord.Object(id=user_id))
    return {"thread_id": str(thread.id), "user_id": str(user_id), "removed": True}


@op("thread.member_info")
async def member_info(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
    user_id = resolve_user_id(args)
    member = await thread.fetch_member(user_id)
    return {
        "id": str(member.id),
        "thread_id": str(member.thread_id),
        "joined_at": str(member.joined_at) if getattr(member, "joined_at", None) else None,
    }


@op("thread.members_list")
async def members_list(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
    members = await thread.fetch_members()
    return [
        {
            "id": str(m.id),
            "thread_id": str(m.thread_id),
            "joined_at": str(m.joined_at) if getattr(m, "joined_at", None) else None,
        }
        for m in members
    ]


@op("thread.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    thread = _resolve_thread(guild, args)
    if ctx.dry_run:
        return plan("thread.delete", thread_id=str(thread.id))
    await thread.delete(reason=args.get("reason"))
    return {"thread_id": str(thread.id), "deleted": True}
