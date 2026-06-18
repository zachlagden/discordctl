from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import user as user_ops
from discordctl.ops.registry import BusContext


def ctx_for(bot, dry_run=False):
    return BusContext(
        bot=bot,
        dry_run=dry_run,
        confirm=not dry_run,
        yes_really=False,
        actor="t",
        write_enabled=True,
        allowed_guild_ids=frozenset({1}),
        default_guild_id=1,
    )


async def test_user_me_serializes_bot_user():
    bot = SimpleNamespace(
        user=SimpleNamespace(id=42, name="ctl", global_name="Ctl", bot=True, avatar="asseturl")
    )
    ctx = ctx_for(bot)
    result = await user_ops.me(ctx, {})
    assert result == {
        "id": "42",
        "name": "ctl",
        "global_name": "Ctl",
        "bot": True,
        "avatar": "asseturl",
    }


async def test_user_get_fetches_and_serializes():
    fetched = SimpleNamespace(id=99, name="bob", global_name=None, bot=False, avatar=None)
    bot = SimpleNamespace(fetch_user=AsyncMock(return_value=fetched))
    ctx = ctx_for(bot)
    result = await user_ops.get(ctx, {"user_id": "99"})
    bot.fetch_user.assert_awaited_once_with(99)
    assert result == {
        "id": "99",
        "name": "bob",
        "global_name": None,
        "bot": False,
        "avatar": None,
    }
