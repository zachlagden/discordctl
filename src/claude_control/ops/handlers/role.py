from __future__ import annotations

import discord

from claude_control.ops import serialize
from claude_control.ops.lookup import resolve_guild, resolve_role
from claude_control.ops.registry import op, plan


def _colour(value):
    if isinstance(value, int):
        return discord.Colour(value)
    return discord.Colour(int(str(value).lstrip("#"), 16))


@op("role.list")
async def list_roles(ctx, args):
    guild = resolve_guild(ctx, args)
    return [serialize.role_dict(r) for r in guild.roles]


@op("role.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    return serialize.role_dict(resolve_role(guild, args))


@op("role.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    name = args["name"]
    if ctx.dry_run:
        return plan("role.create", name=name)
    kwargs = {"name": name, "reason": args.get("reason")}
    if args.get("colour") is not None:
        kwargs["colour"] = _colour(args["colour"])
    if args.get("permissions") is not None:
        kwargs["permissions"] = discord.Permissions(int(args["permissions"]))
    for field in ("hoist", "mentionable"):
        if args.get(field) is not None:
            kwargs[field] = bool(args[field])
    role = await guild.create_role(**kwargs)
    return serialize.role_dict(role)


@op("role.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    role = resolve_role(guild, args)
    fields = {}
    for field in ("name", "hoist", "mentionable"):
        if field in args:
            fields[field] = args[field]
    if args.get("colour") is not None:
        fields["colour"] = _colour(args["colour"])
    if ctx.dry_run:
        return plan("role.edit", role_id=str(role.id), fields=list(fields))
    await role.edit(reason=args.get("reason"), **fields)
    return serialize.role_dict(role)


@op("role.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    role = resolve_role(guild, args)
    if ctx.dry_run:
        return plan("role.delete", role_id=str(role.id), name=role.name)
    await role.delete(reason=args.get("reason"))
    return {"deleted": str(role.id)}


@op("role.move", mutating=True)
async def move(ctx, args):
    guild = resolve_guild(ctx, args)
    role = resolve_role(guild, args)
    position = int(args["position"])
    if ctx.dry_run:
        return plan("role.move", role_id=str(role.id), position=position)
    await role.edit(position=position, reason=args.get("reason"))
    return serialize.role_dict(role)


@op("role.clone", mutating=True)
async def clone(ctx, args):
    guild = resolve_guild(ctx, args)
    role = resolve_role(guild, args)
    if ctx.dry_run:
        return plan("role.clone", role_id=str(role.id))
    new = await guild.create_role(
        name=args.get("name", f"{role.name} copy"),
        permissions=discord.Permissions(role.permissions.value),
        colour=discord.Colour(role.color.value), hoist=role.hoist,
        mentionable=role.mentionable, reason=args.get("reason"),
    )
    return serialize.role_dict(new)


@op("role.permissions_set", mutating=True)
async def permissions_set(ctx, args):
    guild = resolve_guild(ctx, args)
    role = resolve_role(guild, args)
    perms = discord.Permissions(int(args["permissions"]))
    if ctx.dry_run:
        return plan("role.permissions_set", role_id=str(role.id), permissions=str(perms.value))
    await role.edit(permissions=perms, reason=args.get("reason"))
    return serialize.role_dict(role)
