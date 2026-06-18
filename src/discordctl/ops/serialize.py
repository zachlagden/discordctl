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


def message_dict(message: Any) -> dict[str, Any]:
    return {
        "id": _id(message.id),
        "channel_id": _id(message.channel.id),
        "author_id": _id(message.author.id),
        "author": getattr(message.author, "name", None),
        "content": message.content,
        "pinned": getattr(message, "pinned", None),
        "created_at": str(message.created_at) if getattr(message, "created_at", None) else None,
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


def guild_dict(guild: Any) -> dict[str, Any]:
    return {
        "id": _id(guild.id),
        "name": guild.name,
        "owner_id": _id(getattr(guild, "owner_id", None)),
        "member_count": getattr(guild, "member_count", None),
        "description": getattr(guild, "description", None),
    }
