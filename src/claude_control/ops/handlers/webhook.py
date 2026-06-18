from __future__ import annotations

from claude_control.ops import serialize
from claude_control.ops.lookup import resolve_channel, resolve_guild
from claude_control.ops.registry import HandlerError, op, plan


@op("webhook.list")
async def list_webhooks(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    hooks = await channel.webhooks()
    return [serialize.webhook_dict(w) for w in hooks]


@op("webhook.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    name = args["name"]
    if ctx.dry_run:
        return plan("webhook.create", channel_id=str(channel.id), name=name)
    hook = await channel.create_webhook(name=name, reason=args.get("reason"))
    return serialize.webhook_dict(hook)


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
