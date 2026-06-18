from __future__ import annotations

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_category, resolve_guild
from discordctl.ops.registry import op, plan


@op("category.list")
async def list_categories(ctx, args):
    guild = resolve_guild(ctx, args)
    return [serialize.category_dict(c) for c in guild.categories]


@op("category.info")
async def info(ctx, args):
    guild = resolve_guild(ctx, args)
    return serialize.category_dict(resolve_category(guild, args))


@op("category.children")
async def children(ctx, args):
    guild = resolve_guild(ctx, args)
    category = resolve_category(guild, args)
    return [serialize.channel_dict(c) for c in category.channels]


@op("category.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    name = args["name"]
    if ctx.dry_run:
        return plan("category.create", name=name)
    category = await guild.create_category(name, reason=args.get("reason"))
    return serialize.category_dict(category)


@op("category.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    category = resolve_category(guild, args)
    fields = {k: args[k] for k in ("name", "position") if k in args}
    if ctx.dry_run:
        return plan("category.edit", category_id=str(category.id), fields=fields)
    await category.edit(reason=args.get("reason"), **fields)
    return serialize.category_dict(category)


@op("category.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    category = resolve_category(guild, args)
    if ctx.dry_run:
        return plan("category.delete", category_id=str(category.id), name=category.name)
    await category.delete(reason=args.get("reason"))
    return {"deleted": str(category.id)}


@op("category.move", mutating=True)
async def move(ctx, args):
    guild = resolve_guild(ctx, args)
    category = resolve_category(guild, args)
    position = int(args["position"])
    if ctx.dry_run:
        return plan("category.move", category_id=str(category.id), position=position)
    await category.edit(position=position, reason=args.get("reason"))
    return serialize.category_dict(category)
