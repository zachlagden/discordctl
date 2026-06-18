from types import SimpleNamespace

import pytest

from discordctl.ops.registry import BusContext


class FakeRole(SimpleNamespace):
    pass


def make_role(id=10, name="mod", position=2):
    return SimpleNamespace(
        id=id,
        name=name,
        position=position,
        hoist=False,
        mentionable=True,
        managed=False,
        color=SimpleNamespace(value=0x5865F2),
        permissions=SimpleNamespace(value=8),
    )


def make_member(id=100, name="alice", roles=None):
    return SimpleNamespace(
        id=id,
        name=name,
        display_name=name,
        nick=None,
        bot=False,
        roles=roles or [],
        joined_at=None,
        guild_permissions=SimpleNamespace(value=8),
    )


def make_channel(id=200, name="general", type_name="text", position=0, category_id=None):
    return SimpleNamespace(
        id=id,
        name=name,
        position=position,
        type=SimpleNamespace(name=type_name),
        category_id=category_id,
        topic=None,
        nsfw=False,
        slowmode_delay=0,
    )


@pytest.fixture
def fake_ctx():
    return BusContext(
        bot=SimpleNamespace(),
        dry_run=True,
        confirm=False,
        yes_really=False,
        actor="test",
        write_enabled=True,
        allowed_guild_ids=frozenset({1}),
        default_guild_id=1,
    )
