from __future__ import annotations

import discord

from typing import Any


def _id(value: Any) -> str | None:
    return str(value) if value is not None else None


def role_dict(role: Any) -> dict[str, Any]:
    return {
        "id": _id(role.id),
        "name": role.name,
        "position": role.position,
        "color": f"#{role.color.value:06x}",
        "hoist": role.hoist,
        "mentionable": role.mentionable,
        "managed": role.managed,
        "permissions": str(role.permissions.value),
    }


def user_dict(user: Any) -> dict[str, Any]:
    avatar = getattr(user, "avatar", None)
    return {
        "id": _id(getattr(user, "id", None)),
        "name": getattr(user, "name", None),
        "global_name": getattr(user, "global_name", None),
        "bot": getattr(user, "bot", False),
        "avatar": str(avatar) if avatar is not None else None,
    }


def member_dict(member: Any) -> dict[str, Any]:
    return {
        "id": _id(member.id),
        "name": member.name,
        "display_name": getattr(member, "display_name", member.name),
        "nick": getattr(member, "nick", None),
        "bot": getattr(member, "bot", False),
        "role_ids": [_id(r.id) for r in getattr(member, "roles", [])],
        "joined_at": str(member.joined_at) if getattr(member, "joined_at", None) else None,
    }


def channel_dict(channel: Any) -> dict[str, Any]:
    return {
        "id": _id(channel.id),
        "name": getattr(channel, "name", None),
        "type": channel.type.name,
        "position": getattr(channel, "position", None),
        "category_id": _id(getattr(channel, "category_id", None)),
        "topic": getattr(channel, "topic", None),
        "nsfw": getattr(channel, "nsfw", None),
        "slowmode_delay": getattr(channel, "slowmode_delay", None),
    }


def category_dict(category: Any) -> dict[str, Any]:
    return {
        "id": _id(category.id),
        "name": category.name,
        "position": category.position,
        "channel_ids": [_id(c.id) for c in getattr(category, "channels", [])],
    }


def embed_dict(embed: Any) -> dict[str, Any]:
    if hasattr(embed, "to_dict"):
        return embed.to_dict()
    return {
        "title": getattr(embed, "title", None),
        "description": getattr(embed, "description", None),
    }


def attachment_dict(attachment: Any) -> dict[str, Any]:
    return {
        "id": _id(attachment.id),
        "filename": getattr(attachment, "filename", None),
        "url": getattr(attachment, "url", None),
        "size": getattr(attachment, "size", None),
    }


def poll_dict(poll: Any) -> dict[str, Any]:
    question = getattr(poll, "question", None)
    answers = []
    for answer in getattr(poll, "answers", []):
        answers.append(
            {
                "id": _id(getattr(answer, "id", None)),
                "text": getattr(answer, "text", None),
                "vote_count": getattr(answer, "vote_count", None),
            }
        )
    return {
        "question": getattr(question, "text", question),
        "multiple": getattr(poll, "multiple", None),
        "answers": answers,
    }


def message_dict(message: Any) -> dict[str, Any]:
    embeds = getattr(message, "embeds", None) or []
    attachments = getattr(message, "attachments", None) or []
    components = getattr(message, "components", None)
    flags = getattr(message, "flags", None)
    poll = getattr(message, "poll", None)
    return {
        "id": _id(message.id),
        "channel_id": _id(message.channel.id),
        "author_id": _id(message.author.id),
        "author": getattr(message.author, "name", None),
        "content": message.content,
        "pinned": getattr(message, "pinned", None),
        "created_at": str(message.created_at) if getattr(message, "created_at", None) else None,
        "embeds": [embed_dict(e) for e in embeds],
        "attachments": [attachment_dict(a) for a in attachments],
        "components": [c.to_dict() for c in components] if components else [],
        "poll": poll_dict(poll) if poll is not None else None,
        "flags": flags.value if flags is not None else None,
    }


def overwrite_dict(target: Any, overwrite: Any) -> dict[str, Any]:
    allow, deny = overwrite.pair()
    return {
        "target_id": _id(target.id),
        "target_name": getattr(target, "name", None),
        "target_type": "role" if isinstance(target, discord.Role) else "member",
        "allow": str(allow.value),
        "deny": str(deny.value),
    }


def emoji_dict(emoji: Any) -> dict[str, Any]:
    return {"id": _id(emoji.id), "name": emoji.name, "animated": emoji.animated}


def sticker_dict(s: Any) -> dict[str, Any]:
    emoji = getattr(s, "emoji", None)
    fmt = getattr(s, "format", None)
    return {
        "id": _id(getattr(s, "id", None)),
        "name": getattr(s, "name", None),
        "description": getattr(s, "description", None),
        "emoji": str(emoji) if emoji is not None else None,
        "format": str(getattr(fmt, "name", fmt)) if fmt is not None else None,
        "available": getattr(s, "available", None),
        "guild_id": _id(getattr(s, "guild_id", None)),
    }


def stage_dict(i: Any) -> dict[str, Any]:
    privacy_level = getattr(i, "privacy_level", None)
    return {
        "id": _id(getattr(i, "id", None)),
        "guild_id": _id(getattr(getattr(i, "guild", None), "id", None)),
        "channel_id": _id(getattr(i, "channel_id", None)),
        "topic": getattr(i, "topic", None),
        "privacy_level": str(getattr(privacy_level, "name", privacy_level))
        if privacy_level is not None
        else None,
    }


def invite_dict(invite: Any) -> dict[str, Any]:
    return {
        "code": invite.code,
        "url": invite.url,
        "uses": getattr(invite, "uses", None),
        "max_uses": getattr(invite, "max_uses", None),
        "max_age": getattr(invite, "max_age", None),
        "channel_id": _id(getattr(invite.channel, "id", None)) if invite.channel else None,
    }


def webhook_dict(webhook: Any) -> dict[str, Any]:
    return {
        "id": _id(webhook.id),
        "name": webhook.name,
        "channel_id": _id(getattr(webhook, "channel_id", None)),
        "url": getattr(webhook, "url", None),
    }


def thread_dict(thread: Any) -> dict[str, Any]:
    return {
        "id": _id(thread.id),
        "name": thread.name,
        "parent_id": _id(getattr(thread, "parent_id", None)),
        "archived": getattr(thread, "archived", None),
        "locked": getattr(thread, "locked", None),
        "member_count": getattr(thread, "member_count", None),
    }


def scheduled_event_dict(e: Any) -> dict[str, Any]:
    entity_type = getattr(e, "entity_type", None)
    status = getattr(e, "status", None)
    privacy_level = getattr(e, "privacy_level", None)
    start_time = getattr(e, "start_time", None)
    end_time = getattr(e, "end_time", None)
    return {
        "id": _id(getattr(e, "id", None)),
        "guild_id": _id(getattr(e, "guild_id", None)),
        "name": getattr(e, "name", None),
        "description": getattr(e, "description", None),
        "entity_type": str(getattr(entity_type, "name", entity_type))
        if entity_type is not None
        else None,
        "status": str(getattr(status, "name", status)) if status is not None else None,
        "privacy_level": str(getattr(privacy_level, "name", privacy_level))
        if privacy_level is not None
        else None,
        "start_time": str(start_time) if start_time is not None else None,
        "end_time": str(end_time) if end_time is not None else None,
        "channel_id": _id(getattr(e, "channel_id", None)),
        "creator_id": _id(getattr(e, "creator_id", None)),
        "user_count": getattr(e, "user_count", None),
        "location": getattr(e, "location", None),
    }


def automod_rule_dict(r: Any) -> dict[str, Any]:
    event_type = getattr(r, "event_type", None)
    trigger = getattr(r, "trigger", None)
    trigger_type = getattr(trigger, "type", None) if trigger is not None else None
    trigger_metadata: dict[str, Any] = {}
    if trigger is not None and hasattr(trigger, "to_metadata_dict"):
        try:
            trigger_metadata = trigger.to_metadata_dict()
        except Exception:
            trigger_metadata = {}
    actions = []
    for action in getattr(r, "actions", None) or []:
        if hasattr(action, "to_dict"):
            try:
                actions.append(action.to_dict())
                continue
            except Exception:
                pass
        actions.append({"type": str(getattr(getattr(action, "type", None), "name", None))})
    return {
        "id": _id(getattr(r, "id", None)),
        "guild_id": _id(getattr(getattr(r, "guild", None), "id", None)),
        "name": getattr(r, "name", None),
        "creator_id": _id(getattr(r, "creator_id", None)),
        "event_type": str(getattr(event_type, "name", event_type))
        if event_type is not None
        else None,
        "trigger_type": str(getattr(trigger_type, "name", trigger_type))
        if trigger_type is not None
        else None,
        "trigger_metadata": trigger_metadata,
        "actions": actions,
        "enabled": getattr(r, "enabled", None),
        "exempt_roles": [_id(i) for i in getattr(r, "exempt_role_ids", None) or []],
        "exempt_channels": [_id(i) for i in getattr(r, "exempt_channel_ids", None) or []],
    }


def guild_dict(guild: Any) -> dict[str, Any]:
    return {
        "id": _id(guild.id),
        "name": guild.name,
        "owner_id": _id(getattr(guild, "owner_id", None)),
        "member_count": getattr(guild, "member_count", None),
        "description": getattr(guild, "description", None),
    }
