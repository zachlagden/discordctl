from __future__ import annotations

from discordctl.ops import serialize
from discordctl.ops.message_build import build_message_kwargs, perform_send
from discordctl.ops.registry import op, plan


@op("user.me")
async def me(ctx, args):
    return serialize.user_dict(ctx.bot.user)


@op("user.get")
async def get(ctx, args):
    user = await ctx.bot.fetch_user(int(args["user_id"]))
    return serialize.user_dict(user)


@op("user.dm_send", mutating=True)
async def dm_send(ctx, args):
    kwargs = build_message_kwargs(args)
    if ctx.dry_run:
        return plan(
            "user.dm_send",
            user_id=str(args["user_id"]),
            has_embeds=bool(kwargs.get("embeds")),
            has_components=bool(kwargs.get("components")),
            has_files=bool(kwargs.get("files")),
        )
    user = await ctx.bot.fetch_user(int(args["user_id"]))
    dm = await user.create_dm()
    message = await perform_send(ctx, dm, kwargs)
    return serialize.message_dict(message)
