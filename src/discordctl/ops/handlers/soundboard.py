from __future__ import annotations

import base64

import discord

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_guild
from discordctl.ops.registry import HandlerError, op, plan


async def _resolve_sound(guild, args):
    sid = int(args["sound_id"])
    sound = guild.get_soundboard_sound(sid)
    if sound is not None:
        return sound
    sounds = await guild.fetch_soundboard_sounds()
    for s in sounds:
        if s.id == sid:
            return s
    raise HandlerError(f"soundboard sound {sid} not found", code="not_found")


@op("soundboard.list")
async def list_sounds(ctx, args):
    guild = resolve_guild(ctx, args)
    sounds = list(guild.soundboard_sounds)
    if not sounds:
        sounds = await guild.fetch_soundboard_sounds()
    out = {"guild": [serialize.soundboard_sound_dict(s) for s in sounds]}
    if args.get("include_default"):
        defaults = await ctx.bot.fetch_soundboard_default_sounds()
        out["default"] = [serialize.soundboard_sound_dict(s) for s in defaults]
    return out


@op("soundboard.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    sound = await _resolve_sound(guild, args)
    return serialize.soundboard_sound_dict(sound)


@op("soundboard.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    name = str(args["name"])
    if ctx.dry_run:
        return plan("soundboard.create", guild_id=str(guild.id), name=name)
    sound_bytes = base64.b64decode(args["sound_b64"])
    kwargs: dict = {"name": name, "sound": sound_bytes}
    if args.get("volume") is not None:
        kwargs["volume"] = float(args["volume"])
    if args.get("emoji") is not None:
        kwargs["emoji"] = discord.PartialEmoji.from_str(str(args["emoji"]))
    if args.get("reason") is not None:
        kwargs["reason"] = args["reason"]
    sound = await guild.create_soundboard_sound(**kwargs)
    return serialize.soundboard_sound_dict(sound)


@op("soundboard.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    sound = await _resolve_sound(guild, args)
    kwargs: dict = {}
    if args.get("name") is not None:
        kwargs["name"] = str(args["name"])
    if args.get("volume") is not None:
        kwargs["volume"] = float(args["volume"])
    if "emoji" in args:
        emoji = args["emoji"]
        kwargs["emoji"] = discord.PartialEmoji.from_str(str(emoji)) if emoji is not None else None
    if args.get("reason") is not None:
        kwargs["reason"] = args["reason"]
    if ctx.dry_run:
        return plan("soundboard.edit", guild_id=str(guild.id), sound_id=str(sound.id))
    updated = await sound.edit(**kwargs)
    return serialize.soundboard_sound_dict(updated or sound)


@op("soundboard.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    sound = await _resolve_sound(guild, args)
    if ctx.dry_run:
        return plan("soundboard.delete", guild_id=str(guild.id), sound_id=str(sound.id))
    await sound.delete(reason=args.get("reason"))
    return {"deleted": str(sound.id)}
