from __future__ import annotations

from discordctl.ops import serialize
from discordctl.ops.registry import op


@op("user.me")
async def me(ctx, args):
    return serialize.user_dict(ctx.bot.user)


@op("user.get")
async def get(ctx, args):
    user = await ctx.bot.fetch_user(int(args["user_id"]))
    return serialize.user_dict(user)
