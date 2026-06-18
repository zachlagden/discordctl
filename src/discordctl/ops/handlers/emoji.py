from __future__ import annotations

import base64

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_guild
from discordctl.ops.registry import HandlerError, op, plan


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


def _find_emoji(guild, eid):
    match = [e for e in guild.emojis if e.id == eid]
    if not match:
        raise HandlerError(f"emoji {eid} not found", code="not_found")
    return match[0]


@op("emoji.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    return serialize.emoji_dict(_find_emoji(guild, int(args["emoji_id"])))


@op("emoji.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    eid = int(args["emoji_id"])
    emoji = _find_emoji(guild, eid)
    if ctx.dry_run:
        return plan("emoji.edit", emoji_id=str(eid))
    fields = {}
    if "name" in args:
        fields["name"] = args["name"]
    if args.get("roles") is not None:
        fields["roles"] = [guild.get_role(int(r)) for r in args["roles"]]
    await emoji.edit(reason=args.get("reason"), **fields)
    return serialize.emoji_dict(emoji)


@op("emoji.app_list")
async def app_list(ctx, args):
    emojis = await ctx.bot.fetch_application_emojis()
    return [serialize.emoji_dict(e) for e in emojis]


@op("emoji.app_info")
async def app_info(ctx, args):
    emoji = await ctx.bot.fetch_application_emoji(int(args["emoji_id"]))
    return serialize.emoji_dict(emoji)


@op("emoji.app_create", mutating=True)
async def app_create(ctx, args):
    name = args["name"]
    if ctx.dry_run:
        return plan("emoji.app_create", name=name)
    image = base64.b64decode(args["image_b64"])
    emoji = await ctx.bot.create_application_emoji(name=name, image=image)
    return serialize.emoji_dict(emoji)


@op("emoji.app_edit", mutating=True)
async def app_edit(ctx, args):
    eid = int(args["emoji_id"])
    if ctx.dry_run:
        return plan("emoji.app_edit", emoji_id=str(eid))
    emoji = await ctx.bot.fetch_application_emoji(eid)
    edited = await emoji.edit(name=args["name"])
    return serialize.emoji_dict(edited if edited is not None else emoji)


@op("emoji.app_delete", mutating=True)
async def app_delete(ctx, args):
    eid = int(args["emoji_id"])
    if ctx.dry_run:
        return plan("emoji.app_delete", emoji_id=str(eid))
    emoji = await ctx.bot.fetch_application_emoji(eid)
    await emoji.delete()
    return {"deleted": str(eid)}
