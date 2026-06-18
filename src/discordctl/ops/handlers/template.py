from __future__ import annotations

from discordctl.ops import serialize
from discordctl.ops.lookup import resolve_guild
from discordctl.ops.registry import HandlerError, op, plan


async def _resolve_template(guild, code):
    templates = await guild.templates()
    for template in templates:
        if template.code == code:
            return template
    raise HandlerError(f"template {code} not found", code="not_found")


@op("template.list")
async def list_templates(ctx, args):
    guild = resolve_guild(ctx, args)
    templates = await guild.templates()
    return [serialize.template_dict(t) for t in templates]


@op("template.get")
async def get(ctx, args):
    code = str(args["code"])
    template = await ctx.bot.fetch_template(code)
    return serialize.template_dict(template)


@op("template.create", mutating=True)
async def create(ctx, args):
    guild = resolve_guild(ctx, args)
    name = args["name"]
    if ctx.dry_run:
        return plan("template.create", guild_id=str(guild.id), name=name)
    kwargs = {"name": name}
    if args.get("description") is not None:
        kwargs["description"] = str(args["description"])
    template = await guild.create_template(**kwargs)
    return serialize.template_dict(template)


@op("template.sync", mutating=True)
async def sync(ctx, args):
    guild = resolve_guild(ctx, args)
    code = str(args["code"])
    if ctx.dry_run:
        return plan("template.sync", guild_id=str(guild.id), code=code)
    template = await _resolve_template(guild, code)
    template = await template.sync()
    return serialize.template_dict(template)


@op("template.edit", mutating=True)
async def edit(ctx, args):
    guild = resolve_guild(ctx, args)
    code = str(args["code"])
    fields = {}
    if "name" in args:
        fields["name"] = args["name"]
    if "description" in args:
        fields["description"] = args["description"]
    if ctx.dry_run:
        return plan("template.edit", guild_id=str(guild.id), code=code, fields=sorted(fields))
    template = await _resolve_template(guild, code)
    template = await template.edit(**fields)
    return serialize.template_dict(template)


@op("template.delete", mutating=True)
async def delete(ctx, args):
    guild = resolve_guild(ctx, args)
    code = str(args["code"])
    if ctx.dry_run:
        return plan("template.delete", guild_id=str(guild.id), code=code)
    template = await _resolve_template(guild, code)
    await template.delete()
    return {"deleted": code}
