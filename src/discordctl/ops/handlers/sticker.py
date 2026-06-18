from __future__ import annotations

import base64
import io

import discord

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_guild
from discordctl.ops.registry import HandlerError, op, plan


async def _resolve_sticker(guild, args):
    sid = int(args["sticker_id"])
    match = [s for s in guild.stickers if s.id == sid]
    if match:
        return match[0]
    try:
        return await guild.fetch_sticker(sid)
    except discord.NotFound:
        raise HandlerError(f"sticker {sid} not found", code="not_found")


@op("sticker.list")
async def list_stickers(ctx, args):
    guild = resolve_guild(ctx, args)
    return [serialize.sticker_dict(s) for s in guild.stickers]


@op("sticker.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    return serialize.sticker_dict(await _resolve_sticker(guild, args))


@op("sticker.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    name = args["name"]
    emoji = args["emoji"]
    if ctx.dry_run:
        return plan("sticker.create", name=name, emoji=emoji)
    file = discord.File(io.BytesIO(base64.b64decode(args["file_b64"])), filename="sticker")
    sticker = await guild.create_sticker(
        name=name,
        description=args.get("description", ""),
        emoji=emoji,
        file=file,
        reason=args.get("reason"),
    )
    return serialize.sticker_dict(sticker)


@op("sticker.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    sticker = await _resolve_sticker(guild, args)
    fields = {}
    if args.get("name") is not None:
        fields["name"] = args["name"]
    if args.get("description") is not None:
        fields["description"] = args["description"]
    if args.get("emoji") is not None:
        fields["emoji"] = args["emoji"]
    if ctx.dry_run:
        return plan("sticker.edit", sticker_id=str(sticker.id), fields=sorted(fields))
    edited = await sticker.edit(reason=args.get("reason"), **fields)
    return serialize.sticker_dict(edited if edited is not None else sticker)


@op("sticker.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    sticker = await _resolve_sticker(guild, args)
    if ctx.dry_run:
        return plan("sticker.delete", sticker_id=str(sticker.id))
    await sticker.delete(reason=args.get("reason"))
    return {"sticker_id": str(sticker.id), "deleted": True}


@op("sticker.get")
async def get(ctx, args):
    sticker = await ctx.bot.fetch_sticker(int(args["sticker_id"]))
    return serialize.sticker_dict(sticker)


@op("sticker.packs")
async def packs(ctx, args):
    result = await ctx.bot.fetch_premium_sticker_packs()
    return [
        {
            "id": str(getattr(p, "id", None)),
            "name": getattr(p, "name", None),
            "sticker_ids": [str(s.id) for s in getattr(p, "stickers", None) or []],
        }
        for p in result
    ]
