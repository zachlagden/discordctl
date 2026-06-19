from __future__ import annotations

import base64
import datetime

import discord
from discord.http import Route
from discord.utils import MISSING

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_guild
from discordctl.ops.registry import HandlerError, op, plan


@op("guild.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    data = serialize.guild_dict(guild)
    data["counts"] = {
        "roles": len(guild.roles),
        "channels": len(guild.channels),
        "categories": len(guild.categories),
    }
    return data


@op("guild.audit_log")
async def audit_log(ctx, args):
    guild = resolve_guild(ctx, args)
    limit = int(args.get("limit", 25))
    out = []
    async for entry in guild.audit_logs(limit=limit):
        out.append(
            {
                "action": str(entry.action),
                "user_id": str(entry.user.id) if entry.user else None,
                "target_id": str(getattr(entry.target, "id", None)) if entry.target else None,
                "reason": entry.reason,
                "created_at": str(entry.created_at),
            }
        )
    return out


def _decode_image(value):
    if value is None:
        return None
    return base64.b64decode(value)


def _channel_or_none(guild, value):
    if value is None:
        return None
    return guild.get_channel(int(value)) or discord.Object(id=int(value))


def _parse_dt(value):
    if value is None:
        return None
    return datetime.datetime.fromisoformat(value)


_GUILD_EDIT_BOOLS = (
    "community",
    "discoverable",
    "invites_disabled",
    "widget_enabled",
    "raid_alerts_disabled",
    "premium_progress_bar_enabled",
)

_GUILD_EDIT_STRINGS = ("name", "description", "preferred_locale", "vanity_code")

_GUILD_EDIT_IMAGES = ("icon", "banner", "splash", "discovery_splash")

_GUILD_EDIT_CHANNELS = (
    "afk_channel",
    "system_channel",
    "rules_channel",
    "public_updates_channel",
    "safety_alerts_channel",
    "widget_channel",
)

_GUILD_EDIT_ENUMS = {
    "verification_level": discord.VerificationLevel,
    "default_notifications": discord.NotificationLevel,
    "explicit_content_filter": discord.ContentFilter,
    "mfa_level": discord.MFALevel,
}

_GUILD_EDIT_DATETIMES = ("invites_disabled_until", "dms_disabled_until")


def _enum_value(enum_cls, value):
    if isinstance(value, str):
        return enum_cls[value]
    return enum_cls(int(value))


def _build_edit_fields(guild, args):
    fields = {}
    for key in _GUILD_EDIT_STRINGS:
        if key in args:
            fields[key] = args[key]
    for key in _GUILD_EDIT_IMAGES:
        if key in args:
            fields[key] = _decode_image(args[key])
        elif f"{key}_b64" in args:
            fields[key] = _decode_image(args[f"{key}_b64"])
    if "afk_timeout" in args:
        fields["afk_timeout"] = int(args["afk_timeout"])
    for key in _GUILD_EDIT_BOOLS:
        if key in args:
            fields[key] = bool(args[key])
    for key in _GUILD_EDIT_CHANNELS:
        if key in args:
            fields[key] = _channel_or_none(guild, args[key])
        elif f"{key}_id" in args:
            fields[key] = _channel_or_none(guild, args[f"{key}_id"])
    for key, enum_cls in _GUILD_EDIT_ENUMS.items():
        if key in args:
            fields[key] = _enum_value(enum_cls, args[key])
    if "default_message_notifications" in args:
        fields["default_notifications"] = _enum_value(
            discord.NotificationLevel, args["default_message_notifications"]
        )
    if "system_channel_flags" in args:
        fields["system_channel_flags"] = discord.SystemChannelFlags(**args["system_channel_flags"])
    for key in _GUILD_EDIT_DATETIMES:
        if key in args:
            fields[key] = _parse_dt(args[key])
    return fields


@op("guild.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    fields = _build_edit_fields(guild, args)
    if ctx.dry_run:
        plan_fields = sorted(fields)
        return plan("guild.edit", guild_id=str(guild.id), fields=plan_fields)
    await guild.edit(reason=args.get("reason"), **fields)
    return serialize.guild_dict(guild)


@op("guild.prune_count")
async def prune_count(ctx, args):
    guild = resolve_guild(ctx, args)
    days = int(args.get("days", 7))
    role_ids = args.get("role_ids")
    roles = [discord.Object(id=int(r)) for r in role_ids] if role_ids else MISSING
    count = await guild.estimate_pruned_members(days=days, roles=roles)
    return {"days": days, "estimated": count}


@op("guild.prune", mutating=True)
async def prune(ctx, args):
    guild = resolve_guild(ctx, args)
    days = int(args.get("days", 7))
    role_ids = args.get("role_ids")
    roles = [discord.Object(id=int(r)) for r in role_ids] if role_ids else MISSING
    compute = bool(args.get("compute_prune_count", True))
    if ctx.dry_run:
        return plan(
            "guild.prune",
            guild_id=str(guild.id),
            days=days,
            role_ids=[str(r) for r in role_ids] if role_ids else [],
        )
    pruned = await guild.prune_members(
        days=days,
        compute_prune_count=compute,
        roles=roles,
        reason=args.get("reason"),
    )
    return {"days": days, "pruned": pruned}


@op("guild.onboarding_get")
async def onboarding_get(ctx, args):
    guild = resolve_guild(ctx, args)
    onboarding = await guild.onboarding()
    return serialize.onboarding_dict(onboarding)


@op("guild.onboarding_edit", mutating=True)
async def onboarding_edit(ctx, args):
    guild = resolve_guild(ctx, args)
    fields = {}
    if "enabled" in args:
        fields["enabled"] = bool(args["enabled"])
    if "mode" in args:
        fields["mode"] = discord.OnboardingMode[args["mode"]]
    if "default_channel_ids" in args:
        fields["default_channels"] = [
            discord.Object(id=int(c)) for c in args["default_channel_ids"]
        ]
    if ctx.dry_run:
        return plan("guild.onboarding_edit", guild_id=str(guild.id), fields=sorted(fields))
    onboarding = await guild.edit_onboarding(reason=args.get("reason"), **fields)
    return serialize.onboarding_dict(onboarding)


@op("guild.welcome_screen_get")
async def welcome_screen_get(ctx, args):
    guild = resolve_guild(ctx, args)
    screen = await guild.welcome_screen()
    return serialize.welcome_screen_dict(screen)


def _build_welcome_channels(args):
    channels = []
    for entry in args["welcome_channels"]:
        channels.append(
            discord.WelcomeChannel(
                channel=discord.Object(id=int(entry["channel_id"])),
                description=entry["description"],
                emoji=entry.get("emoji"),
            )
        )
    return channels


@op("guild.welcome_screen_edit", mutating=True)
async def welcome_screen_edit(ctx, args):
    guild = resolve_guild(ctx, args)
    fields = {}
    if "description" in args:
        fields["description"] = args["description"]
    if "enabled" in args:
        fields["enabled"] = bool(args["enabled"])
    if "welcome_channels" in args:
        fields["welcome_channels"] = _build_welcome_channels(args)
    if ctx.dry_run:
        return plan("guild.welcome_screen_edit", guild_id=str(guild.id), fields=sorted(fields))
    screen = await guild.edit_welcome_screen(reason=args.get("reason"), **fields)
    return serialize.welcome_screen_dict(screen)


@op("guild.widget_get")
async def widget_get(ctx, args):
    guild = resolve_guild(ctx, args)
    widget = await guild.widget()
    return serialize.widget_dict(widget)


@op("guild.widget_edit", mutating=True)
async def widget_edit(ctx, args):
    guild = resolve_guild(ctx, args)
    fields = {}
    if "enabled" in args:
        fields["enabled"] = bool(args["enabled"])
    if "channel_id" in args:
        channel_id = args["channel_id"]
        fields["channel"] = discord.Object(id=int(channel_id)) if channel_id is not None else None
    if ctx.dry_run:
        return plan("guild.widget_edit", guild_id=str(guild.id), fields=sorted(fields))
    await guild.edit_widget(reason=args.get("reason"), **fields)
    return {"guild_id": str(guild.id), "edited": sorted(fields)}


@op("guild.integrations_list")
async def integrations_list(ctx, args):
    guild = resolve_guild(ctx, args)
    integrations = await guild.integrations()
    return [serialize.integration_dict(i) for i in integrations]


@op("guild.integration_delete", mutating=True)
async def integration_delete(ctx, args):
    guild = resolve_guild(ctx, args)
    integration_id = int(args["integration_id"])
    if ctx.dry_run:
        return plan(
            "guild.integration_delete",
            guild_id=str(guild.id),
            integration_id=str(integration_id),
        )
    integrations = await guild.integrations()
    match = [i for i in integrations if i.id == integration_id]
    if not match:
        raise HandlerError(f"integration {integration_id} not found", code="not_found")
    await match[0].delete(reason=args.get("reason"))
    return {"deleted": str(integration_id)}


@op("guild.incident_actions_set", mutating=True)
async def incident_actions_set(ctx, args):
    guild = resolve_guild(ctx, args)
    fields = {}
    if "invites_disabled_until" in args:
        fields["invites_disabled_until"] = _parse_dt(args["invites_disabled_until"])
    if "dms_disabled_until" in args:
        fields["dms_disabled_until"] = _parse_dt(args["dms_disabled_until"])
    if not fields:
        raise HandlerError("invites_disabled_until or dms_disabled_until required", code="bad_args")
    if ctx.dry_run:
        return plan("guild.incident_actions_set", guild_id=str(guild.id), fields=sorted(fields))
    edit_fields = {k: (v if v is not None else MISSING) for k, v in fields.items()}
    await guild.edit(reason=args.get("reason"), **edit_fields)
    return {"guild_id": str(guild.id), "set": sorted(fields)}


@op("guild.preview")
async def preview(ctx, args):
    guild = resolve_guild(ctx, args)
    preview = await ctx.bot.fetch_guild_preview(guild.id)
    icon = getattr(preview, "icon", None)
    return {
        "id": serialize._id(getattr(preview, "id", None)),
        "name": getattr(preview, "name", None),
        "description": getattr(preview, "description", None),
        "approximate_member_count": getattr(preview, "approximate_member_count", None),
        "approximate_presence_count": getattr(preview, "approximate_presence_count", None),
        "features": list(getattr(preview, "features", None) or []),
        "icon": str(icon) if icon is not None else None,
        "emoji_count": len(getattr(preview, "emojis", None) or []),
        "sticker_count": len(getattr(preview, "stickers", None) or []),
    }


@op("guild.voice_regions")
async def voice_regions(ctx, args):
    guild = resolve_guild(ctx, args)
    route = Route("GET", "/guilds/{guild_id}/regions", guild_id=guild.id)
    data = await ctx.bot.http.request(route)
    return [serialize.voice_region_dict(r) for r in data or []]


@op("guild.vanity_url")
async def vanity_url(ctx, args):
    guild = resolve_guild(ctx, args)
    invite = await guild.vanity_invite()
    if invite is None:
        return {"vanity": None}
    return {
        "code": getattr(invite, "code", None),
        "url": getattr(invite, "url", None),
        "uses": getattr(invite, "uses", None),
    }
