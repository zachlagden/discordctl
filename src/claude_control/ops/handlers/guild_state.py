from __future__ import annotations

from typing import Any

from claude_control.ops import serialize
from claude_control.ops.lookup import resolve_guild
from claude_control.ops.registry import HandlerError, op, plan


def build_snapshot(guild: Any) -> dict[str, Any]:
    return {
        "guild": serialize.guild_dict(guild),
        "roles": [serialize.role_dict(r) for r in sorted(guild.roles, key=lambda r: r.position)],
        "categories": [serialize.category_dict(c) for c in sorted(guild.categories, key=lambda c: c.position)],
        "channels": [serialize.channel_dict(c) for c in sorted(guild.channels, key=lambda c: getattr(c, "position", 0))],
    }


def _diff_section(current: list[dict], desired: list[dict]) -> dict[str, list]:
    cur_by_name = {i["name"]: i for i in current if i.get("name")}
    des_by_name = {i["name"]: i for i in desired if i.get("name")}
    create = [des_by_name[n] for n in des_by_name if n not in cur_by_name]
    delete = [cur_by_name[n] for n in cur_by_name if n not in des_by_name]
    edit = [des_by_name[n] for n in des_by_name if n in cur_by_name and des_by_name[n] != cur_by_name[n]]
    return {"create": create, "edit": edit, "delete": delete}


def diff_snapshots(current: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
    return {
        section: _diff_section(current.get(section, []), desired.get(section, []))
        for section in ("roles", "categories", "channels")
    }


@op("guild.snapshot")
async def snapshot(ctx, args):
    guild = resolve_guild(ctx, args)
    return build_snapshot(guild)


@op("guild.diff")
async def diff(ctx, args):
    guild = resolve_guild(ctx, args)
    desired = args.get("desired")
    if desired is None:
        raise HandlerError("desired snapshot required (args.desired)", code="bad_args")
    return diff_snapshots(build_snapshot(guild), desired)


@op("guild.apply", mutating=True)
async def apply(ctx, args):
    guild = resolve_guild(ctx, args)
    desired = args.get("desired")
    if desired is None:
        raise HandlerError("desired snapshot required (args.desired)", code="bad_args")
    changes = diff_snapshots(build_snapshot(guild), desired)

    deletions = sum(len(changes[s]["delete"]) for s in changes)
    if deletions and not ctx.yes_really:
        raise HandlerError(
            f"apply would delete {deletions} entities; pass yes_really", code="needs_yes_really")

    if ctx.dry_run:
        return plan("guild.apply", guild_id=str(guild.id), changes=changes)

    applied = {"roles_created": [], "categories_created": []}
    for role in changes["roles"]["create"]:
        created = await guild.create_role(name=role["name"], reason="guild.apply")
        applied["roles_created"].append(str(created.id))
    for category in changes["categories"]["create"]:
        created = await guild.create_category(category["name"], reason="guild.apply")
        applied["categories_created"].append(str(created.id))
    if ctx.yes_really:
        for role in changes["roles"]["delete"]:
            existing = [r for r in guild.roles if r.name == role["name"]]
            if existing:
                await existing[0].delete(reason="guild.apply")
    applied["changes"] = changes
    return applied
