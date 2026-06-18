from __future__ import annotations

from claude_control.ops import serialize
from claude_control.ops.lookup import resolve_guild
from claude_control.ops.registry import op, plan


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
        out.append({
            "action": str(entry.action),
            "user_id": str(entry.user.id) if entry.user else None,
            "target_id": str(getattr(entry.target, "id", None)) if entry.target else None,
            "reason": entry.reason,
            "created_at": str(entry.created_at),
        })
    return out


@op("guild.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    fields = {k: args[k] for k in ("name", "description") if k in args}
    if ctx.dry_run:
        return plan("guild.edit", guild_id=str(guild.id), fields=fields)
    await guild.edit(reason=args.get("reason"), **fields)
    return serialize.guild_dict(guild)
