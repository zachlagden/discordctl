from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discordctl.ops.handlers import guild as guild_ops
from discordctl.ops.handlers import role as role_ops
from discordctl.ops.registry import BusContext, HandlerError


def make_guild():
    return SimpleNamespace(
        id=1,
        name="DigiGrow",
        owner_id=5,
        roles=[],
        channels=[],
        categories=[],
        members=[],
        onboarding=AsyncMock(),
        edit_onboarding=AsyncMock(),
        welcome_screen=AsyncMock(),
        edit_welcome_screen=AsyncMock(),
        widget=AsyncMock(),
        edit_widget=AsyncMock(),
        integrations=AsyncMock(return_value=[]),
    )


def ctx_for(guild, dry_run):
    return BusContext(
        bot=SimpleNamespace(get_guild=lambda gid: guild),
        dry_run=dry_run,
        confirm=not dry_run,
        yes_really=False,
        actor="t",
        write_enabled=True,
        allowed_guild_ids=frozenset({1}),
        default_guild_id=1,
    )


async def test_onboarding_get_read():
    guild = make_guild()
    guild.onboarding = AsyncMock(
        return_value=SimpleNamespace(
            guild=guild, enabled=True, mode=None, default_channel_ids=[200], prompts=[]
        )
    )
    result = await guild_ops.onboarding_get(ctx_for(guild, True), {})
    guild.onboarding.assert_awaited_once()
    assert result["enabled"] is True
    assert result["default_channel_ids"] == ["200"]


async def test_onboarding_edit_dry_run():
    guild = make_guild()
    result = await guild_ops.onboarding_edit(
        ctx_for(guild, True), {"enabled": True, "default_channel_ids": [200]}
    )
    assert result["planned"] is True
    guild.edit_onboarding.assert_not_called()


async def test_onboarding_edit_live():
    guild = make_guild()
    guild.edit_onboarding = AsyncMock(
        return_value=SimpleNamespace(
            guild=guild, enabled=False, mode=None, default_channel_ids=[], prompts=[]
        )
    )
    await guild_ops.onboarding_edit(ctx_for(guild, False), {"enabled": False, "mode": "advanced"})
    guild.edit_onboarding.assert_awaited_once()
    kwargs = guild.edit_onboarding.await_args.kwargs
    assert kwargs["enabled"] is False
    assert str(kwargs["mode"]) == "OnboardingMode.advanced"


async def test_welcome_screen_get_read():
    guild = make_guild()
    guild.welcome_screen = AsyncMock(
        return_value=SimpleNamespace(description="welcome", enabled=True, welcome_channels=[])
    )
    result = await guild_ops.welcome_screen_get(ctx_for(guild, True), {})
    assert result["description"] == "welcome"


async def test_welcome_screen_edit_dry_run():
    guild = make_guild()
    result = await guild_ops.welcome_screen_edit(
        ctx_for(guild, True), {"description": "hi", "enabled": True}
    )
    assert result["planned"] is True
    guild.edit_welcome_screen.assert_not_called()


async def test_welcome_screen_edit_live_builds_channels():
    guild = make_guild()
    guild.edit_welcome_screen = AsyncMock(
        return_value=SimpleNamespace(description="hi", enabled=True, welcome_channels=[])
    )
    await guild_ops.welcome_screen_edit(
        ctx_for(guild, False),
        {
            "description": "hi",
            "welcome_channels": [{"channel_id": 200, "description": "general", "emoji": None}],
        },
    )
    guild.edit_welcome_screen.assert_awaited_once()
    kwargs = guild.edit_welcome_screen.await_args.kwargs
    assert kwargs["welcome_channels"][0].channel.id == 200


async def test_widget_get_read():
    guild = make_guild()
    guild.widget = AsyncMock(
        return_value=SimpleNamespace(
            id=1,
            name="DigiGrow",
            invite_url="http://x",
            json_url="http://x.json",
            presence_count=3,
            channels=[],
            members=[],
        )
    )
    result = await guild_ops.widget_get(ctx_for(guild, True), {})
    assert result["presence_count"] == 3


async def test_widget_edit_dry_run():
    guild = make_guild()
    result = await guild_ops.widget_edit(ctx_for(guild, True), {"enabled": True})
    assert result["planned"] is True
    guild.edit_widget.assert_not_called()


async def test_widget_edit_live():
    guild = make_guild()
    await guild_ops.widget_edit(ctx_for(guild, False), {"enabled": True, "channel_id": 200})
    guild.edit_widget.assert_awaited_once()
    kwargs = guild.edit_widget.await_args.kwargs
    assert kwargs["enabled"] is True
    assert kwargs["channel"].id == 200


async def test_integrations_list_read():
    guild = make_guild()
    guild.integrations = AsyncMock(
        return_value=[
            SimpleNamespace(
                id=9, name="twitch", type="twitch", enabled=True, account=None, user=None
            )
        ]
    )
    result = await guild_ops.integrations_list(ctx_for(guild, True), {})
    assert result[0]["id"] == "9"


async def test_integration_delete_dry_run():
    guild = make_guild()
    result = await guild_ops.integration_delete(ctx_for(guild, True), {"integration_id": 9})
    assert result["planned"] is True
    guild.integrations.assert_not_called()


async def test_integration_delete_live():
    guild = make_guild()
    integration = SimpleNamespace(id=9, delete=AsyncMock())
    guild.integrations = AsyncMock(return_value=[integration])
    result = await guild_ops.integration_delete(ctx_for(guild, False), {"integration_id": 9})
    integration.delete.assert_awaited_once()
    assert result["deleted"] == "9"


async def test_integration_delete_not_found():
    guild = make_guild()
    guild.integrations = AsyncMock(return_value=[])
    with pytest.raises(HandlerError):
        await guild_ops.integration_delete(ctx_for(guild, False), {"integration_id": 9})


async def test_role_member_counts():
    role_a = SimpleNamespace(id=1, name="everyone")
    role_b = SimpleNamespace(id=2, name="mod")
    guild = make_guild()
    guild.roles = [role_a, role_b]
    guild.members = [
        SimpleNamespace(roles=[role_a, role_b]),
        SimpleNamespace(roles=[role_a]),
    ]
    result = await role_ops.member_counts(ctx_for(guild, True), {})
    assert result["source"] == "cache"
    by_id = {c["role_id"]: c["count"] for c in result["counts"]}
    assert by_id["1"] == 2
    assert by_id["2"] == 1
