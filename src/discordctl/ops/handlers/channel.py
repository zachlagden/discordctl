from __future__ import annotations

import discord

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_channel, resolve_guild
from discordctl.ops.registry import HandlerError, op, plan

_CREATORS = {
    "text": "create_text_channel",
    "voice": "create_voice_channel",
    "forum": "create_forum",
    "stage": "create_stage_channel",
    "category": "create_category",
}

_CREATE_FIELDS = {
    "text": (
        "topic",
        "nsfw",
        "slowmode_delay",
        "position",
        "default_auto_archive_duration",
        "default_thread_slowmode_delay",
    ),
    "voice": (
        "nsfw",
        "position",
        "bitrate",
        "user_limit",
        "rtc_region",
        "video_quality_mode",
        "slowmode_delay",
    ),
    "stage": (
        "nsfw",
        "position",
        "bitrate",
        "user_limit",
        "rtc_region",
        "video_quality_mode",
    ),
    "forum": (
        "topic",
        "nsfw",
        "slowmode_delay",
        "position",
        "default_auto_archive_duration",
        "default_thread_slowmode_delay",
        "default_reaction_emoji",
        "available_tags",
        "default_sort_order",
        "default_forum_layout",
    ),
    "category": ("position",),
}

_FORUM_LAYOUT_KW = {"forum": "default_layout"}
_FORUM_SORT_KW = {"forum": "default_sort_order"}

_EDIT_FIELDS = {
    "text": (
        "name",
        "topic",
        "nsfw",
        "slowmode_delay",
        "position",
        "default_auto_archive_duration",
        "default_thread_slowmode_delay",
    ),
    "news": (
        "name",
        "topic",
        "nsfw",
        "slowmode_delay",
        "position",
        "default_auto_archive_duration",
        "default_thread_slowmode_delay",
    ),
    "voice": (
        "name",
        "nsfw",
        "slowmode_delay",
        "position",
        "bitrate",
        "user_limit",
        "rtc_region",
        "video_quality_mode",
    ),
    "stage": (
        "name",
        "nsfw",
        "slowmode_delay",
        "position",
        "bitrate",
        "user_limit",
        "rtc_region",
        "video_quality_mode",
    ),
    "forum": (
        "name",
        "topic",
        "nsfw",
        "slowmode_delay",
        "position",
        "default_auto_archive_duration",
        "default_thread_slowmode_delay",
        "available_tags",
        "default_reaction_emoji",
    ),
    "category": ("name", "nsfw", "position"),
}

_ENUM_BUILDERS = {
    "video_quality_mode": lambda v: discord.VideoQualityMode(int(v)),
    "default_sort_order": lambda v: discord.ForumOrderType(int(v)),
    "default_forum_layout": lambda v: discord.ForumLayoutType(int(v)),
    "default_layout": lambda v: discord.ForumLayoutType(int(v)),
}


def _build_tags(raw):
    tags = []
    for entry in raw or []:
        tags.append(
            discord.ForumTag(
                name=entry["name"],
                emoji=entry.get("emoji"),
                moderated=bool(entry.get("moderated", False)),
            )
        )
    return tags


def _build_overwrites(guild, raw):
    overwrites = {}
    for entry in raw or []:
        if entry.get("role_id") is not None:
            target = guild.get_role(int(entry["role_id"]))
        elif entry.get("user_id") is not None:
            target = guild.get_member(int(entry["user_id"]))
        else:
            raise HandlerError("overwrite entry needs role_id or user_id", code="bad_args")
        if target is None:
            raise HandlerError("overwrite target not found", code="not_found")
        mapping = {}
        for name in entry.get("allow") or []:
            mapping[name] = True
        for name in entry.get("deny") or []:
            mapping[name] = False
        try:
            overwrites[target] = discord.PermissionOverwrite(**mapping)
        except (ValueError, TypeError) as exc:
            raise HandlerError(f"invalid permission name: {exc}", code="bad_args")
    return overwrites


def _coerce_create_field(field, value):
    if field in _ENUM_BUILDERS:
        return _ENUM_BUILDERS[field](value)
    if field == "available_tags":
        return _build_tags(value)
    return value


@op("channel.list")
async def list_channels(ctx, args):
    guild = resolve_guild(ctx, args)
    return [serialize.channel_dict(c) for c in guild.channels]


@op("channel.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    return serialize.channel_dict(resolve_channel(guild, args))


@op("channel.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    ctype = str(args.get("type", "text"))
    method_name = _CREATORS.get(ctype)
    if method_name is None:
        raise HandlerError(f"unsupported channel type {ctype!r}", code="bad_args")
    supported = _CREATE_FIELDS[ctype]
    for field in ("topic", "nsfw"):
        if args.get(field) is not None and field not in supported:
            raise HandlerError(f"{ctype} channels do not support {field!r}", code="bad_args")
    name = args["name"]
    if ctx.dry_run:
        return plan("channel.create", type=ctype, name=name)
    kwargs = {}
    if ctype != "category" and args.get("category_id") is not None:
        kwargs["category"] = guild.get_channel(int(args["category_id"]))
    for field in supported:
        if args.get(field) is None:
            continue
        kw = field
        if field == "default_sort_order":
            kw = _FORUM_SORT_KW.get(ctype, field)
        elif field == "default_forum_layout":
            kw = _FORUM_LAYOUT_KW.get(ctype, field)
        kwargs[kw] = _coerce_create_field(kw, args[field])
    if args.get("permission_overwrites") is not None:
        kwargs["overwrites"] = _build_overwrites(guild, args["permission_overwrites"])
    try:
        channel = await getattr(guild, method_name)(name, reason=args.get("reason"), **kwargs)
    except TypeError as exc:
        raise HandlerError(f"invalid argument for {ctype} channel: {exc}", code="bad_args")
    return serialize.channel_dict(channel)


def _build_edit_fields(guild, channel, ctype, args):
    fields = {}
    for field in _EDIT_FIELDS.get(ctype, _EDIT_FIELDS["text"]):
        if field in args:
            value = args[field]
            if field in _ENUM_BUILDERS:
                value = _ENUM_BUILDERS[field](value)
            elif field == "available_tags":
                value = _build_tags(value)
            fields[field] = value
    if "default_sort_order" in args and ctype == "forum":
        fields["default_sort_order"] = discord.ForumOrderType(int(args["default_sort_order"]))
    if "default_forum_layout" in args and ctype == "forum":
        fields["default_layout"] = discord.ForumLayoutType(int(args["default_forum_layout"]))
    if "flags" in args:
        flags = discord.ChannelFlags()
        for name, value in args["flags"].items():
            setattr(flags, name, bool(value))
        fields["flags"] = flags
    if "category_id" in args:
        fields["category"] = (
            guild.get_channel(int(args["category_id"])) if args["category_id"] is not None else None
        )
    if args.get("type") is not None:
        fields["type"] = discord.ChannelType[str(args["type"])]
    if args.get("sync_permissions"):
        fields["sync_permissions"] = True
    if "permission_overwrites" in args:
        fields["overwrites"] = _build_overwrites(guild, args["permission_overwrites"])
    return fields


@op("channel.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    ctype = getattr(channel.type, "name", "text")
    fields = _build_edit_fields(guild, channel, ctype, args)
    if ctx.dry_run:
        plan_fields = sorted(fields)
        return plan("channel.edit", channel_id=str(channel.id), fields=plan_fields)
    try:
        await channel.edit(reason=args.get("reason"), **fields)
    except TypeError as exc:
        raise HandlerError(f"invalid argument for channel edit: {exc}", code="bad_args")
    return serialize.channel_dict(channel)


@op("channel.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("channel.delete", channel_id=str(channel.id), name=channel.name)
    await channel.delete(reason=args.get("reason"))
    return {"deleted": str(channel.id)}


@op("channel.move", mutating=True)
async def move(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    position = int(args["position"])
    if ctx.dry_run:
        return plan("channel.move", channel_id=str(channel.id), position=position)
    await channel.edit(position=position, reason=args.get("reason"))
    return serialize.channel_dict(channel)


@op("channel.clone", mutating=True)
async def clone(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("channel.clone", channel_id=str(channel.id))
    new = await channel.clone(name=args.get("name"), reason=args.get("reason"))
    return serialize.channel_dict(new)


@op("channel.sync", mutating=True)
async def sync(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("channel.sync", channel_id=str(channel.id))
    await channel.edit(sync_permissions=True, reason=args.get("reason"))
    return {"synced": str(channel.id)}


@op("channel.follow", mutating=True)
async def follow(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    target_id = int(args["target_channel_id"])
    if ctx.dry_run:
        return plan(
            "channel.follow",
            channel_id=str(channel.id),
            target_channel_id=str(target_id),
        )
    destination = guild.get_channel(target_id)
    if destination is None:
        raise HandlerError(f"target channel {target_id} not found", code="not_found")
    webhook = await channel.follow(destination=destination, reason=args.get("reason"))
    return {"channel_id": str(channel.id), "webhook_id": str(webhook.id)}


@op("channel.voice_status_set", mutating=True)
async def voice_status_set(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    status = args.get("status")
    if ctx.dry_run:
        return plan("channel.voice_status_set", channel_id=str(channel.id), status=status)
    await channel.edit(status=status, reason=args.get("reason"))
    return {"channel_id": str(channel.id), "status": status}


@op("channel.typing", mutating=True)
async def typing(ctx, args):
    guild = resolve_guild(ctx, args)
    channel = resolve_channel(guild, args)
    if ctx.dry_run:
        return plan("channel.typing", channel_id=str(channel.id))
    async with channel.typing():
        pass
    return {"channel_id": str(channel.id)}
