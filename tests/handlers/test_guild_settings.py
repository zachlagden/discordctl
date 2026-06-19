import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import guild as guild_ops
from discordctl.ops.registry import BusContext


def make_guild():
    channel = SimpleNamespace(id=200, name="general")
    return SimpleNamespace(
        id=1,
        name="DigiGrow",
        owner_id=5,
        member_count=42,
        description=None,
        roles=[],
        channels=[channel],
        categories=[],
        get_channel=lambda cid: channel if cid == 200 else None,
        edit=AsyncMock(),
        vanity_invite=AsyncMock(),
    )


def ctx_for(guild, dry_run, bot=None):
    return BusContext(
        bot=bot or SimpleNamespace(get_guild=lambda gid: guild),
        dry_run=dry_run,
        confirm=not dry_run,
        yes_really=False,
        actor="t",
        write_enabled=True,
        allowed_guild_ids=frozenset({1}),
        default_guild_id=1,
    )


def bot_for(guild, **extra):
    return SimpleNamespace(get_guild=lambda gid: guild, **extra)


async def test_edit_dry_run_does_not_call_edit():
    guild = make_guild()
    icon_b64 = base64.b64encode(b"icon").decode()
    result = await guild_ops.edit(
        ctx_for(guild, True),
        {
            "name": "New",
            "verification_level": "high",
            "icon": icon_b64,
            "system_channel": "200",
            "afk_timeout": 300,
        },
    )
    assert result["planned"] is True
    assert "verification_level" in result["fields"]
    guild.edit.assert_not_called()


async def test_edit_live_converts_fields():
    guild = make_guild()
    icon_b64 = base64.b64encode(b"icon").decode()
    await guild_ops.edit(
        ctx_for(guild, False),
        {
            "name": "New",
            "verification_level": "high",
            "default_notifications": "only_mentions",
            "explicit_content_filter": "all_members",
            "icon": icon_b64,
            "system_channel": "200",
            "system_channel_flags": {"join_notifications": True},
            "afk_timeout": 300,
            "preferred_locale": "en-US",
            "premium_progress_bar_enabled": True,
        },
    )
    guild.edit.assert_awaited_once()
    kwargs = guild.edit.await_args.kwargs
    assert kwargs["name"] == "New"
    assert kwargs["verification_level"].name == "high"
    assert kwargs["icon"] == b"icon"
    assert kwargs["system_channel"].id == 200
    assert kwargs["afk_timeout"] == 300
    assert kwargs["premium_progress_bar_enabled"] is True


async def test_edit_community_live_forwards_flag():
    guild = make_guild()
    await guild_ops.edit(
        ctx_for(guild, False),
        {
            "community": True,
            "rules_channel": "200",
            "public_updates_channel": "200",
        },
    )
    guild.edit.assert_awaited_once()
    kwargs = guild.edit.await_args.kwargs
    assert kwargs["community"] is True
    assert kwargs["rules_channel"].id == 200
    assert kwargs["public_updates_channel"].id == 200


async def test_edit_community_dry_run_does_not_call_edit():
    guild = make_guild()
    result = await guild_ops.edit(ctx_for(guild, True), {"community": True})
    assert result["planned"] is True
    assert "community" in result["fields"]
    guild.edit.assert_not_called()


async def test_edit_full_surface_forwards_channel_enum_datetime():
    guild = make_guild()
    await guild_ops.edit(
        ctx_for(guild, False),
        {
            "discoverable": True,
            "invites_disabled": False,
            "widget_enabled": True,
            "widget_channel_id": "200",
            "mfa_level": "require_2fa",
            "afk_channel": "200",
            "invites_disabled_until": "2026-07-01T00:00:00+00:00",
            "unknown_setting": "ignored",
        },
    )
    guild.edit.assert_awaited_once()
    kwargs = guild.edit.await_args.kwargs
    assert kwargs["discoverable"] is True
    assert kwargs["invites_disabled"] is False
    assert kwargs["widget_enabled"] is True
    assert kwargs["widget_channel"].id == 200
    assert kwargs["mfa_level"].name == "require_2fa"
    assert kwargs["afk_channel"].id == 200
    assert kwargs["invites_disabled_until"].year == 2026
    assert "unknown_setting" not in kwargs


async def test_edit_image_accepts_b64_suffix():
    guild = make_guild()
    banner = base64.b64encode(b"banner").decode()
    await guild_ops.edit(ctx_for(guild, False), {"banner_b64": banner})
    kwargs = guild.edit.await_args.kwargs
    assert kwargs["banner"] == b"banner"


async def test_incident_actions_dry_run():
    guild = make_guild()
    result = await guild_ops.incident_actions_set(
        ctx_for(guild, True),
        {"invites_disabled_until": "2026-07-01T00:00:00+00:00"},
    )
    assert result["planned"] is True
    guild.edit.assert_not_called()


async def test_incident_actions_live_calls_edit():
    guild = make_guild()
    await guild_ops.incident_actions_set(
        ctx_for(guild, False),
        {"invites_disabled_until": "2026-07-01T00:00:00+00:00", "dms_disabled_until": None},
    )
    guild.edit.assert_awaited_once()
    kwargs = guild.edit.await_args.kwargs
    assert "invites_disabled_until" in kwargs


async def test_preview_read():
    guild = make_guild()
    preview = SimpleNamespace(
        id=1,
        name="DigiGrow",
        description="d",
        approximate_member_count=10,
        approximate_presence_count=3,
        features=["COMMUNITY"],
        icon=None,
        emojis=[1, 2],
        stickers=[],
    )
    bot = bot_for(guild, fetch_guild_preview=AsyncMock(return_value=preview))
    result = await guild_ops.preview(ctx_for(guild, True, bot=bot), {})
    assert result["id"] == "1"
    assert result["approximate_member_count"] == 10
    assert result["emoji_count"] == 2


async def test_voice_regions_uses_http():
    guild = make_guild()
    http = SimpleNamespace(
        request=AsyncMock(return_value=[{"id": "us-east", "name": "US East", "optimal": True}])
    )
    bot = bot_for(guild, http=http)
    result = await guild_ops.voice_regions(ctx_for(guild, True, bot=bot), {})
    http.request.assert_awaited_once()
    assert result[0]["id"] == "us-east"


async def test_vanity_url_none():
    guild = make_guild()
    guild.vanity_invite = AsyncMock(return_value=None)
    result = await guild_ops.vanity_url(ctx_for(guild, True), {})
    assert result["vanity"] is None


async def test_vanity_url_present():
    guild = make_guild()
    guild.vanity_invite = AsyncMock(
        return_value=SimpleNamespace(code="abc", url="http://x/abc", uses=4)
    )
    result = await guild_ops.vanity_url(ctx_for(guild, True), {})
    assert result["code"] == "abc"
    assert result["uses"] == 4
