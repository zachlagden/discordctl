from __future__ import annotations

import discord
from discord.utils import MISSING

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_channel, resolve_guild
from discordctl.ops.message_build import build_message_kwargs
from discordctl.ops.registry import HandlerError, op, plan

_WEBHOOK_SEND_KEYS = frozenset(
    {
        "content",
        "embeds",
        "files",
        "allowed_mentions",
        "tts",
    }
)

_WEBHOOK_EDIT_KEYS = frozenset(
    {
        "content",
        "embeds",
        "allowed_mentions",
    }
)


def _thread(args):
    thread_id = args.get("thread_id")
    return discord.Object(id=int(thread_id)) if thread_id else MISSING


@op("webhook.list")
async def list_webhooks(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    hooks = await channel.webhooks()
    return [serialize.webhook_dict(w) for w in hooks]


@op("webhook.guild_list")
async def guild_list(ctx, args):
    guild = resolve_guild(ctx, args)
    hooks = await guild.webhooks()
    return [serialize.webhook_dict(w) for w in hooks]


@op("webhook.info")
async def info(ctx, args):
    wh = await ctx.bot.fetch_webhook(int(args["webhook_id"]))
    return serialize.webhook_dict(wh)


@op("webhook.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    name = args["name"]
    if ctx.dry_run:
        return plan("webhook.create", channel_id=str(channel.id), name=name)
    hook = await channel.create_webhook(name=name, reason=args.get("reason"))
    return serialize.webhook_dict(hook)


@op("webhook.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    wid = int(args["webhook_id"])
    if ctx.dry_run:
        return plan("webhook.edit", webhook_id=str(wid))
    wh = await ctx.bot.fetch_webhook(wid)
    channel_id = args.get("channel_id")
    channel = guild.get_channel(int(channel_id)) if channel_id else MISSING
    name = args.get("name") if args.get("name") is not None else MISSING
    wh = await wh.edit(name=name, channel=channel, reason=args.get("reason"))
    return serialize.webhook_dict(wh)


@op("webhook.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    wid = int(args["webhook_id"])
    hooks = await channel.webhooks()
    match = [w for w in hooks if w.id == wid]
    if not match:
        raise HandlerError(f"webhook {wid} not found", code="not_found")
    if ctx.dry_run:
        return plan("webhook.delete", webhook_id=str(wid))
    await match[0].delete(reason=args.get("reason"))
    return {"deleted": str(wid)}


@op("webhook.execute", mutating=True)
async def execute(ctx, args):
    wid = int(args["webhook_id"])
    if ctx.dry_run:
        return plan("webhook.execute", webhook_id=str(wid))
    if args.get("components") is not None:
        raise HandlerError("components are not supported on webhook.execute", code="unsupported")
    wh = await ctx.bot.fetch_webhook(wid)
    built = build_message_kwargs(args)
    kwargs = {k: v for k, v in built.items() if k in _WEBHOOK_SEND_KEYS}
    if args.get("username") is not None:
        kwargs["username"] = str(args["username"])
    if args.get("avatar_url") is not None:
        kwargs["avatar_url"] = str(args["avatar_url"])
    thread = _thread(args)
    if thread is not MISSING:
        kwargs["thread"] = thread
    kwargs["wait"] = True
    msg = await wh.send(**kwargs)
    if msg is None:
        return {"sent": True}
    return serialize.message_dict(msg)


@op("webhook.message_get")
async def message_get(ctx, args):
    wh = await ctx.bot.fetch_webhook(int(args["webhook_id"]))
    m = await wh.fetch_message(int(args["message_id"]), thread=_thread(args))
    return serialize.message_dict(m)


@op("webhook.message_edit", mutating=True)
async def message_edit(ctx, args):
    wid = int(args["webhook_id"])
    mid = int(args["message_id"])
    if ctx.dry_run:
        return plan("webhook.message_edit", webhook_id=str(wid), message_id=str(mid))
    wh = await ctx.bot.fetch_webhook(wid)
    built = build_message_kwargs(args, edit=True)
    kwargs = {k: v for k, v in built.items() if k in _WEBHOOK_EDIT_KEYS}
    m = await wh.edit_message(mid, thread=_thread(args), **kwargs)
    return serialize.message_dict(m)


@op("webhook.message_delete", mutating=True)
async def message_delete(ctx, args):
    wid = int(args["webhook_id"])
    mid = int(args["message_id"])
    if ctx.dry_run:
        return plan("webhook.message_delete", webhook_id=str(wid), message_id=str(mid))
    wh = await ctx.bot.fetch_webhook(wid)
    await wh.delete_message(mid, thread=_thread(args))
    return {"deleted": str(mid)}
