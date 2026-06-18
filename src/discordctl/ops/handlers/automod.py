from __future__ import annotations

import datetime

import discord

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_guild
from discordctl.ops.registry import HandlerError, op, plan

_EVENT_TYPES = {
    "message_send": discord.AutoModRuleEventType.message_send,
    "member_update": discord.AutoModRuleEventType.member_update,
}

_TRIGGER_TYPES = {
    "keyword": discord.AutoModRuleTriggerType.keyword,
    "spam": discord.AutoModRuleTriggerType.spam,
    "keyword_preset": discord.AutoModRuleTriggerType.keyword_preset,
    "mention_spam": discord.AutoModRuleTriggerType.mention_spam,
    "member_profile": discord.AutoModRuleTriggerType.member_profile,
}

_ACTION_TYPES = {
    "block_message": discord.AutoModRuleActionType.block_message,
    "timeout": discord.AutoModRuleActionType.timeout,
    "send_alert_message": discord.AutoModRuleActionType.send_alert_message,
}

_PRESET_NAMES = {"profanity", "sexual_content", "slurs"}


async def _resolve_rule(guild, args):
    rid = int(args["rule_id"])
    try:
        return await guild.fetch_automod_rule(rid)
    except discord.NotFound:
        raise HandlerError(f"automod rule {rid} not found", code="not_found")


def _build_trigger(trigger_type, metadata):
    metadata = metadata or {}
    kwargs = {"type": _TRIGGER_TYPES[trigger_type]}
    if metadata.get("keyword_filter") is not None:
        kwargs["keyword_filter"] = list(metadata["keyword_filter"])
    if metadata.get("regex_patterns") is not None:
        kwargs["regex_patterns"] = list(metadata["regex_patterns"])
    if metadata.get("allow_list") is not None:
        kwargs["allow_list"] = list(metadata["allow_list"])
    if metadata.get("presets") is not None:
        names = {str(p) for p in metadata["presets"]}
        unknown = names - _PRESET_NAMES
        if unknown:
            raise HandlerError(f"unknown automod presets {sorted(unknown)}", code="bad_args")
        kwargs["presets"] = discord.AutoModPresets(**{name: True for name in names})
    limit = metadata.get("mention_total_limit", metadata.get("mention_limit"))
    if limit is not None:
        kwargs["mention_limit"] = int(limit)
    if metadata.get("mention_raid_protection") is not None:
        kwargs["mention_raid_protection"] = bool(metadata["mention_raid_protection"])
    return discord.AutoModTrigger(**kwargs)


def _build_actions(actions):
    built = []
    for raw in actions or []:
        action_type = str(raw.get("type"))
        if action_type not in _ACTION_TYPES:
            raise HandlerError(f"unknown action type {action_type!r}", code="bad_args")
        meta = raw.get("metadata") or {}
        kwargs = {"type": _ACTION_TYPES[action_type]}
        if meta.get("channel_id") is not None:
            kwargs["channel_id"] = int(meta["channel_id"])
        if meta.get("custom_message") is not None:
            kwargs["custom_message"] = str(meta["custom_message"])
        duration = meta.get("duration_seconds", meta.get("duration"))
        if duration is not None:
            kwargs["duration"] = datetime.timedelta(seconds=int(duration))
        built.append(discord.AutoModRuleAction(**kwargs))
    return built


def _exempt_objects(ids):
    return [discord.Object(id=int(i)) for i in ids or []]


@op("automod.list")
async def list_rules(ctx, args):
    guild = resolve_guild(ctx, args)
    return [serialize.automod_rule_dict(r) for r in await guild.fetch_automod_rules()]


@op("automod.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    return serialize.automod_rule_dict(await _resolve_rule(guild, args))


@op("automod.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    name = args["name"]
    event = str(args["event_type"])
    if event not in _EVENT_TYPES:
        raise HandlerError(f"unknown event_type {event!r}", code="bad_args")
    trigger_type = str(args["trigger_type"])
    if trigger_type not in _TRIGGER_TYPES:
        raise HandlerError(f"unknown trigger_type {trigger_type!r}", code="bad_args")
    trigger = _build_trigger(trigger_type, args.get("trigger_metadata"))
    actions = _build_actions(args.get("actions"))
    if ctx.dry_run:
        return plan(
            "automod.create",
            name=name,
            event_type=event,
            trigger_type=trigger_type,
            action_count=len(actions),
        )
    rule = await guild.create_automod_rule(
        name=name,
        event_type=_EVENT_TYPES[event],
        trigger=trigger,
        actions=actions,
        enabled=bool(args.get("enabled", False)),
        exempt_roles=_exempt_objects(args.get("exempt_roles")),
        exempt_channels=_exempt_objects(args.get("exempt_channels")),
        reason=args.get("reason"),
    )
    return serialize.automod_rule_dict(rule)


@op("automod.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    rule = await _resolve_rule(guild, args)
    fields = {}
    if args.get("name") is not None:
        fields["name"] = args["name"]
    if args.get("event_type") is not None:
        event = str(args["event_type"])
        if event not in _EVENT_TYPES:
            raise HandlerError(f"unknown event_type {event!r}", code="bad_args")
        fields["event_type"] = _EVENT_TYPES[event]
    if args.get("trigger_type") is not None or args.get("trigger_metadata") is not None:
        trigger_type = str(args.get("trigger_type", getattr(rule.trigger.type, "name", "")))
        if trigger_type not in _TRIGGER_TYPES:
            raise HandlerError(f"unknown trigger_type {trigger_type!r}", code="bad_args")
        fields["trigger"] = _build_trigger(trigger_type, args.get("trigger_metadata"))
    if args.get("actions") is not None:
        fields["actions"] = _build_actions(args["actions"])
    if args.get("enabled") is not None:
        fields["enabled"] = bool(args["enabled"])
    if args.get("exempt_roles") is not None:
        fields["exempt_roles"] = _exempt_objects(args["exempt_roles"])
    if args.get("exempt_channels") is not None:
        fields["exempt_channels"] = _exempt_objects(args["exempt_channels"])
    if ctx.dry_run:
        return plan("automod.edit", rule_id=str(rule.id), fields=sorted(fields))
    await rule.edit(reason=args.get("reason"), **fields)
    return serialize.automod_rule_dict(rule)


@op("automod.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    rule = await _resolve_rule(guild, args)
    if ctx.dry_run:
        return plan("automod.delete", rule_id=str(rule.id))
    await rule.delete(reason=args.get("reason"))
    return {"rule_id": str(rule.id), "deleted": True}
