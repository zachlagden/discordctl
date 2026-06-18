from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import discord

from discordctl.ops.handlers import automod as automod_ops
from discordctl.ops.registry import BusContext, HandlerError


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


def fake_rule(rid=20):
    trigger = discord.AutoModTrigger(
        type=discord.AutoModRuleTriggerType.keyword, keyword_filter=["bad"]
    )
    action = discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)
    return SimpleNamespace(
        id=rid,
        guild=SimpleNamespace(id=1),
        name="filter",
        creator_id=99,
        event_type=discord.AutoModRuleEventType.message_send,
        trigger=trigger,
        actions=[action],
        enabled=True,
        exempt_role_ids=[5],
        exempt_channel_ids=[6],
        edit=AsyncMock(),
        delete=AsyncMock(),
    )


def guild_with(rule=None, create_rule=None):
    async def fetch_one(rid):
        if rule is None:
            raise discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "x")
        return rule

    async def fetch_all():
        return [rule] if rule else []

    return SimpleNamespace(
        id=1,
        fetch_automod_rules=fetch_all,
        fetch_automod_rule=fetch_one,
        create_automod_rule=create_rule or AsyncMock(),
    )


async def test_automod_list():
    guild = guild_with(fake_rule())
    result = await automod_ops.list_rules(ctx_for(guild, True), {})
    assert result[0]["name"] == "filter"
    assert result[0]["event_type"] == "message_send"
    assert result[0]["trigger_type"] == "keyword"
    assert result[0]["trigger_metadata"]["keyword_filter"] == ["bad"]
    assert result[0]["exempt_roles"] == ["5"]
    assert result[0]["exempt_channels"] == ["6"]


async def test_automod_info_not_found():
    guild = guild_with()
    with pytest.raises(HandlerError) as exc:
        await automod_ops.info(ctx_for(guild, True), {"rule_id": 20})
    assert exc.value.code == "not_found"


async def test_automod_create_dry_run():
    guild = guild_with()
    args = {
        "name": "filter",
        "event_type": "message_send",
        "trigger_type": "keyword",
        "trigger_metadata": {"keyword_filter": ["bad"]},
        "actions": [{"type": "block_message"}],
    }
    result = await automod_ops.create(ctx_for(guild, True), args)
    assert result["planned"] is True
    guild.create_automod_rule.assert_not_called()


async def test_automod_create_live():
    created = fake_rule()
    guild = guild_with(create_rule=AsyncMock(return_value=created))
    args = {
        "name": "filter",
        "event_type": "message_send",
        "trigger_type": "keyword",
        "trigger_metadata": {"keyword_filter": ["bad"], "allow_list": ["ok"]},
        "actions": [
            {"type": "timeout", "metadata": {"duration_seconds": 60}},
            {"type": "send_alert_message", "metadata": {"channel_id": 777}},
        ],
        "enabled": True,
        "exempt_roles": [5],
        "exempt_channels": [6],
    }
    result = await automod_ops.create(ctx_for(guild, False), args)
    assert result["name"] == "filter"
    guild.create_automod_rule.assert_awaited_once()
    kwargs = guild.create_automod_rule.await_args.kwargs
    assert kwargs["event_type"] == discord.AutoModRuleEventType.message_send
    assert kwargs["trigger"].type == discord.AutoModRuleTriggerType.keyword
    assert kwargs["trigger"].keyword_filter == ["bad"]
    assert len(kwargs["actions"]) == 2
    assert kwargs["enabled"] is True
    assert [int(o.id) for o in kwargs["exempt_roles"]] == [5]
    assert [int(o.id) for o in kwargs["exempt_channels"]] == [6]


async def test_automod_create_bad_trigger_type():
    guild = guild_with()
    args = {
        "name": "x",
        "event_type": "message_send",
        "trigger_type": "nope",
        "actions": [],
    }
    with pytest.raises(HandlerError) as exc:
        await automod_ops.create(ctx_for(guild, True), args)
    assert exc.value.code == "bad_args"


async def test_automod_create_bad_action_type():
    guild = guild_with()
    args = {
        "name": "x",
        "event_type": "message_send",
        "trigger_type": "keyword",
        "actions": [{"type": "explode"}],
    }
    with pytest.raises(HandlerError) as exc:
        await automod_ops.create(ctx_for(guild, True), args)
    assert exc.value.code == "bad_args"


async def test_automod_edit_dry_run():
    rule = fake_rule()
    guild = guild_with(rule)
    result = await automod_ops.edit(ctx_for(guild, True), {"rule_id": 20, "name": "new"})
    assert result["planned"] is True
    rule.edit.assert_not_called()


async def test_automod_edit_live():
    rule = fake_rule()
    guild = guild_with(rule)
    args = {
        "rule_id": 20,
        "name": "new",
        "enabled": False,
        "trigger_metadata": {"keyword_filter": ["worse"]},
        "actions": [{"type": "block_message"}],
    }
    await automod_ops.edit(ctx_for(guild, False), args)
    rule.edit.assert_awaited_once()
    kwargs = rule.edit.await_args.kwargs
    assert kwargs["name"] == "new"
    assert kwargs["enabled"] is False
    assert kwargs["trigger"].keyword_filter == ["worse"]
    assert len(kwargs["actions"]) == 1


async def test_automod_delete_dry_run():
    rule = fake_rule()
    guild = guild_with(rule)
    result = await automod_ops.delete(ctx_for(guild, True), {"rule_id": 20})
    assert result["planned"] is True
    rule.delete.assert_not_called()


async def test_automod_delete_live():
    rule = fake_rule()
    guild = guild_with(rule)
    result = await automod_ops.delete(ctx_for(guild, False), {"rule_id": 20})
    assert result["deleted"] is True
    rule.delete.assert_awaited_once()
