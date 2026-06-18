from __future__ import annotations

import base64
import datetime

import discord

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_guild
from discordctl.ops.registry import HandlerError, op, plan

_ENTITY_TYPES = {
    "stage_instance": discord.EntityType.stage_instance,
    "voice": discord.EntityType.voice,
    "external": discord.EntityType.external,
}

_PRIVACY_LEVELS = {
    "guild_only": discord.PrivacyLevel.guild_only,
}

_EVENT_STATUS = {
    "scheduled": discord.EventStatus.scheduled,
    "active": discord.EventStatus.active,
    "completed": discord.EventStatus.completed,
    "canceled": discord.EventStatus.canceled,
}


def _parse_time(value):
    try:
        return datetime.datetime.fromisoformat(str(value))
    except ValueError:
        raise HandlerError(f"invalid ISO 8601 datetime {value!r}", code="bad_args")


async def _resolve_event(guild, args):
    eid = int(args["event_id"])
    event = guild.get_scheduled_event(eid)
    if event is None:
        try:
            event = await guild.fetch_scheduled_event(eid)
        except discord.NotFound:
            event = None
    if event is None:
        raise HandlerError(f"scheduled event {eid} not found", code="not_found")
    return event


@op("event.list")
async def list_events(ctx, args):
    guild = resolve_guild(ctx, args)
    return [serialize.scheduled_event_dict(e) for e in guild.scheduled_events]


@op("event.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    return serialize.scheduled_event_dict(await _resolve_event(guild, args))


@op("event.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    name = args["name"]
    kind = str(args["entity_type"])
    if kind not in _ENTITY_TYPES:
        raise HandlerError(f"unknown entity_type {kind!r}", code="bad_args")
    privacy = str(args.get("privacy_level", "guild_only"))
    if privacy not in _PRIVACY_LEVELS:
        raise HandlerError(f"unknown privacy_level {privacy!r}", code="bad_args")
    start_time = _parse_time(args["start_time"])
    end_time = _parse_time(args["end_time"]) if args.get("end_time") is not None else None
    if kind == "external":
        if args.get("location") is None:
            raise HandlerError("external events require location", code="bad_args")
        if end_time is None:
            raise HandlerError("external events require end_time", code="bad_args")
    elif args.get("channel_id") is None:
        raise HandlerError(f"{kind} events require channel_id", code="bad_args")
    if ctx.dry_run:
        return plan("event.create", name=name, entity_type=kind)
    kwargs = {
        "name": name,
        "start_time": start_time,
        "entity_type": _ENTITY_TYPES[kind],
        "privacy_level": _PRIVACY_LEVELS[privacy],
    }
    if args.get("description") is not None:
        kwargs["description"] = args["description"]
    if end_time is not None:
        kwargs["end_time"] = end_time
    if kind == "external":
        kwargs["location"] = args["location"]
    else:
        kwargs["channel"] = discord.Object(id=int(args["channel_id"]))
    if args.get("image_b64") is not None:
        kwargs["image"] = base64.b64decode(args["image_b64"])
    event = await guild.create_scheduled_event(reason=args.get("reason"), **kwargs)
    return serialize.scheduled_event_dict(event)


@op("event.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    event = await _resolve_event(guild, args)
    fields = {}
    if args.get("name") is not None:
        fields["name"] = args["name"]
    if args.get("description") is not None:
        fields["description"] = args["description"]
    if args.get("location") is not None:
        fields["location"] = args["location"]
    if args.get("start_time") is not None:
        fields["start_time"] = _parse_time(args["start_time"])
    if args.get("end_time") is not None:
        fields["end_time"] = _parse_time(args["end_time"])
    if args.get("channel_id") is not None:
        fields["channel"] = discord.Object(id=int(args["channel_id"]))
    if args.get("entity_type") is not None:
        kind = str(args["entity_type"])
        if kind not in _ENTITY_TYPES:
            raise HandlerError(f"unknown entity_type {kind!r}", code="bad_args")
        fields["entity_type"] = _ENTITY_TYPES[kind]
    if args.get("privacy_level") is not None:
        privacy = str(args["privacy_level"])
        if privacy not in _PRIVACY_LEVELS:
            raise HandlerError(f"unknown privacy_level {privacy!r}", code="bad_args")
        fields["privacy_level"] = _PRIVACY_LEVELS[privacy]
    if args.get("status") is not None:
        status = str(args["status"])
        if status not in _EVENT_STATUS:
            raise HandlerError(f"unknown status {status!r}", code="bad_args")
        fields["status"] = _EVENT_STATUS[status]
    if ctx.dry_run:
        return plan("event.edit", event_id=str(event.id), fields=sorted(fields))
    await event.edit(reason=args.get("reason"), **fields)
    return serialize.scheduled_event_dict(event)


@op("event.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    event = await _resolve_event(guild, args)
    if ctx.dry_run:
        return plan("event.delete", event_id=str(event.id))
    await event.delete(reason=args.get("reason"))
    return {"event_id": str(event.id), "deleted": True}


@op("event.users")
async def users(ctx, args):
    guild = resolve_guild(ctx, args)
    event = await _resolve_event(guild, args)
    limit = int(args.get("limit", 100))
    return [serialize.user_dict(u) async for u in event.users(limit=limit)]
