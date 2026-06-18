from types import SimpleNamespace

from discordctl.ops.handlers import bot as bot_ops
from discordctl.ops.registry import BusContext


def make_ctx(bot):
    return BusContext(
        bot=bot,
        dry_run=False,
        confirm=False,
        yes_really=False,
        actor="t",
        write_enabled=True,
        allowed_guild_ids=frozenset(),
        default_guild_id=None,
    )


async def test_ping_returns_latency():
    ctx = make_ctx(SimpleNamespace(latency=0.042))
    result = await bot_ops.ping(ctx, {})
    assert result["latency_ms"] == 42


async def test_version():
    import discordctl

    ctx = make_ctx(SimpleNamespace())
    result = await bot_ops.version(ctx, {})
    assert result["version"] == discordctl.__version__
