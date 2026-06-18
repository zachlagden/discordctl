from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import thread as thread_ops
from discordctl.ops.registry import BusContext


def make_guild():
    thr = SimpleNamespace(
        id=400, name="help", parent_id=200, archived=False, locked=False, member_count=3
    )
    forum = SimpleNamespace(
        id=200,
        name="forum",
        type=SimpleNamespace(name="forum"),
        create_thread=AsyncMock(return_value=SimpleNamespace(thread=thr)),
    )
    guild = SimpleNamespace(
        id=1, threads=[thr], channels=[forum], get_channel=lambda cid: forum if cid == 200 else None
    )
    return guild, forum, thr


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


async def test_list_active():
    guild, forum, thr = make_guild()
    result = await thread_ops.list_active(ctx_for(guild, True), {})
    assert result[0]["id"] == "400"


async def test_create_forum_post_live():
    guild, forum, thr = make_guild()
    await thread_ops.create_forum_post(
        ctx_for(guild, False), {"channel_id": 200, "name": "Q", "content": "body"}
    )
    forum.create_thread.assert_awaited_once()


async def test_create_forum_post_dry_run():
    guild, forum, thr = make_guild()
    result = await thread_ops.create_forum_post(
        ctx_for(guild, True), {"channel_id": 200, "name": "Q", "content": "body"}
    )
    assert result["planned"] is True
    forum.create_thread.assert_not_awaited()


async def test_history_falls_back_to_get_channel():
    message = SimpleNamespace(
        id=900,
        channel=SimpleNamespace(id=400),
        author=SimpleNamespace(id=7, name="zach"),
        content="hi",
        pinned=False,
        created_at=None,
    )

    async def history(limit):
        yield message

    thr = SimpleNamespace(
        id=400,
        name="help",
        parent_id=200,
        archived=False,
        locked=False,
        member_count=3,
        history=history,
    )
    guild = SimpleNamespace(
        id=1, get_thread=lambda tid: None, get_channel=lambda cid: thr if cid == 400 else None
    )
    result = await thread_ops.history(ctx_for(guild, True), {"thread_id": 400})
    assert len(result) == 1
    assert result[0]["id"] == "900"
    assert result[0]["content"] == "hi"
