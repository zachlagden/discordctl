from __future__ import annotations

import base64

from claude_control.ops import serialize
from claude_control.ops.lookup import resolve_guild
from claude_control.ops.registry import HandlerError, op, plan


@op("emoji.list")
async def list_emojis(ctx, args):
    guild = resolve_guild(ctx, args)
    return [serialize.emoji_dict(e) for e in guild.emojis]


@op("emoji.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    name = args["name"]
    if ctx.dry_run:
        return plan("emoji.create", name=name)
    image = base64.b64decode(args["image_b64"])
    emoji = await guild.create_custom_emoji(name=name, image=image, reason=args.get("reason"))
    return serialize.emoji_dict(emoji)


@op("emoji.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    eid = int(args["emoji_id"])
    match = [e for e in guild.emojis if e.id == eid]
    if not match:
        raise HandlerError(f"emoji {eid} not found", code="not_found")
    if ctx.dry_run:
        return plan("emoji.delete", emoji_id=str(eid))
    await match[0].delete(reason=args.get("reason"))
    return {"deleted": str(eid)}
