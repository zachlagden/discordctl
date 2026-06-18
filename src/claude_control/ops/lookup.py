from __future__ import annotations

from typing import Any

from claude_control.ops.registry import BusContext, HandlerError


def resolve_guild(ctx: BusContext, args: dict[str, Any]) -> Any:
    raw = args.get("guild_id", ctx.default_guild_id)
    if raw is None:
        raise HandlerError("guild_id required (no default configured)", code="bad_args")
    gid = int(raw)
    if ctx.allowed_guild_ids and gid not in ctx.allowed_guild_ids:
        raise HandlerError(f"guild {gid} is not in the allowlist", code="forbidden")
    guild = ctx.bot.get_guild(gid)
    if guild is None:
        raise HandlerError(f"guild {gid} not found (is the bot a member?)", code="not_found")
    return guild


def _by_id_or_name(
    items: list[Any], args: dict[str, Any], id_key: str, name_key: str, label: str,
    getter=None,
) -> Any:
    if args.get(id_key) is not None:
        target_id = int(args[id_key])
        if getter is not None:
            found = getter(target_id)
            if found is not None:
                return found
        for item in items:
            if item.id == target_id:
                return item
        raise HandlerError(f"{label} {target_id} not found", code="not_found")
    if args.get(name_key) is not None:
        name = str(args[name_key])
        matches = [i for i in items if getattr(i, "name", None) == name]
        if not matches:
            raise HandlerError(f"{label} named {name!r} not found", code="not_found")
        if len(matches) > 1:
            raise HandlerError(
                f"{len(matches)} {label}s match {name!r}; pass {id_key}", code="ambiguous"
            )
        return matches[0]
    raise HandlerError(f"{id_key} or {name_key} required", code="bad_args")


def resolve_role(guild: Any, args: dict[str, Any], key: str = "role_id") -> Any:
    return _by_id_or_name(
        list(guild.roles), args, key, "role_name", "role", getattr(guild, "get_role", None)
    )


def resolve_channel(guild: Any, args: dict[str, Any], key: str = "channel_id") -> Any:
    return _by_id_or_name(
        list(guild.channels), args, key, "channel_name", "channel",
        getattr(guild, "get_channel", None),
    )


def resolve_category(guild: Any, args: dict[str, Any], key: str = "category_id") -> Any:
    return _by_id_or_name(
        list(guild.categories), args, key, "category_name", "category",
        getattr(guild, "get_channel", None),
    )


async def resolve_member(guild: Any, args: dict[str, Any], key: str = "user_id") -> Any:
    if args.get(key) is not None:
        uid = int(args[key])
        member = guild.get_member(uid)
        if member is None:
            member = await guild.fetch_member(uid)
        if member is None:
            raise HandlerError(f"member {uid} not found", code="not_found")
        return member
    name = args.get("user_name")
    if name is not None:
        matches = [m for m in guild.members if name in (m.name, getattr(m, "nick", None), m.display_name)]
        if not matches:
            raise HandlerError(f"member {name!r} not found in cache", code="not_found")
        if len(matches) > 1:
            raise HandlerError(f"{len(matches)} members match {name!r}; pass user_id", code="ambiguous")
        return matches[0]
    raise HandlerError(f"{key} or user_name required", code="bad_args")


def resolve_user_id(args: dict[str, Any], key: str = "user_id") -> int:
    if args.get(key) is None:
        raise HandlerError(f"{key} required", code="bad_args")
    return int(args[key])
