from __future__ import annotations

import discordctl
from discordctl.ops.registry import REGISTRY, op


@op("bot.ping")
async def ping(ctx, args):
    return {"latency_ms": round(ctx.bot.latency * 1000)}


@op("bot.version")
async def version(ctx, args):
    return {"version": discordctl.__version__}


@op("bot.guilds")
async def guilds(ctx, args):
    return [
        {"id": str(g.id), "name": g.name, "member_count": getattr(g, "member_count", None)}
        for g in ctx.bot.guilds
    ]


@op("bot.stats")
async def stats(ctx, args):
    return {"guilds": len(list(ctx.bot.guilds)), "ops": len(REGISTRY.ops())}
