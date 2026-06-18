from types import SimpleNamespace
from unittest.mock import AsyncMock

from discordctl.ops.handlers import thread as thread_ops
from discordctl.ops.registry import BusContext


def make_thread(tid=400):
    return SimpleNamespace(
        id=tid,
        name="help",
        parent_id=200,
        archived=False,
        locked=False,
        member_count=3,
        edit=AsyncMock(),
        join=AsyncMock(),
        leave=AsyncMock(),
        add_user=AsyncMock(),
        remove_user=AsyncMock(),
        delete=AsyncMock(),
        fetch_member=AsyncMock(return_value=SimpleNamespace(id=7, thread_id=tid, joined_at=None)),
        fetch_members=AsyncMock(
            return_value=[
                SimpleNamespace(id=7, thread_id=tid, joined_at=None),
                SimpleNamespace(id=8, thread_id=tid, joined_at=None),
            ]
        ),
    )


def make_guild():
    thr = make_thread()
    new_thread = make_thread(401)
    message = SimpleNamespace(create_thread=AsyncMock(return_value=new_thread))
    channel = SimpleNamespace(
        id=200,
        name="general",
        create_thread=AsyncMock(return_value=new_thread),
        fetch_message=AsyncMock(return_value=message),
    )
    guild = SimpleNamespace(
        id=1,
        threads=[thr],
        channels=[channel],
        get_thread=lambda tid: thr if tid == 400 else None,
        get_channel=lambda cid: channel if cid == 200 else None,
    )
    return guild, channel, message, thr, new_thread


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


async def test_create_dry_run():
    guild, channel, _m, _t, _nt = make_guild()
    result = await thread_ops.create(ctx_for(guild, True), {"channel_id": 200, "name": "topic"})
    assert result["planned"] is True
    channel.create_thread.assert_not_awaited()


async def test_create_live_passes_only_provided_kwargs():
    guild, channel, _m, _t, new_thread = make_guild()
    result = await thread_ops.create(
        ctx_for(guild, False),
        {"channel_id": 200, "name": "topic", "type": "private", "slowmode_delay": 10},
    )
    channel.create_thread.assert_awaited_once()
    kwargs = channel.create_thread.await_args.kwargs
    assert kwargs["name"] == "topic"
    assert kwargs["type"].name == "private_thread"
    assert kwargs["slowmode_delay"] == 10
    assert "auto_archive_duration" not in kwargs
    assert "invitable" not in kwargs
    assert result["id"] == "401"


async def test_create_from_message_live():
    guild, channel, message, _t, _nt = make_guild()
    result = await thread_ops.create_from_message(
        ctx_for(guild, False),
        {"channel_id": 200, "message_id": 900, "name": "spinoff"},
    )
    channel.fetch_message.assert_awaited_once_with(900)
    message.create_thread.assert_awaited_once()
    assert result["id"] == "401"


async def test_create_from_message_dry_run():
    guild, channel, message, _t, _nt = make_guild()
    result = await thread_ops.create_from_message(
        ctx_for(guild, True),
        {"channel_id": 200, "message_id": 900, "name": "spinoff"},
    )
    assert result["planned"] is True
    channel.fetch_message.assert_not_awaited()
    message.create_thread.assert_not_awaited()


async def test_edit_whitelists_fields():
    guild, _c, _m, thr, _nt = make_guild()
    await thread_ops.edit(
        ctx_for(guild, False),
        {
            "thread_id": 400,
            "name": "renamed",
            "slowmode_delay": 5,
            "reason": "tidy",
            "bogus": "drop me",
            "member_count": 99,
        },
    )
    thr.edit.assert_awaited_once()
    kwargs = thr.edit.await_args.kwargs
    assert kwargs["name"] == "renamed"
    assert kwargs["slowmode_delay"] == 5
    assert kwargs["reason"] == "tidy"
    assert "bogus" not in kwargs
    assert "member_count" not in kwargs


async def test_edit_applied_tags_wrapped():
    guild, _c, _m, thr, _nt = make_guild()
    await thread_ops.edit(ctx_for(guild, False), {"thread_id": 400, "applied_tags": [11, 22]})
    kwargs = thr.edit.await_args.kwargs
    assert [t.id for t in kwargs["applied_tags"]] == [11, 22]


async def test_edit_dry_run():
    guild, _c, _m, thr, _nt = make_guild()
    result = await thread_ops.edit(ctx_for(guild, True), {"thread_id": 400, "name": "renamed"})
    assert result["planned"] is True
    thr.edit.assert_not_awaited()


async def test_archive_and_lock_live():
    guild, _c, _m, thr, _nt = make_guild()
    await thread_ops.archive(ctx_for(guild, False), {"thread_id": 400})
    assert thr.edit.await_args.kwargs["archived"] is True
    await thread_ops.lock(ctx_for(guild, False), {"thread_id": 400})
    assert thr.edit.await_args.kwargs["locked"] is True


async def test_join_leave_dry_run_vs_live():
    guild, _c, _m, thr, _nt = make_guild()
    await thread_ops.join(ctx_for(guild, True), {"thread_id": 400})
    thr.join.assert_not_awaited()
    await thread_ops.join(ctx_for(guild, False), {"thread_id": 400})
    thr.join.assert_awaited_once()
    await thread_ops.leave(ctx_for(guild, True), {"thread_id": 400})
    thr.leave.assert_not_awaited()
    await thread_ops.leave(ctx_for(guild, False), {"thread_id": 400})
    thr.leave.assert_awaited_once()


async def test_member_add_dry_run_vs_live():
    guild, _c, _m, thr, _nt = make_guild()
    result = await thread_ops.member_add(ctx_for(guild, True), {"thread_id": 400, "user_id": 7})
    assert result["planned"] is True
    thr.add_user.assert_not_awaited()
    await thread_ops.member_add(ctx_for(guild, False), {"thread_id": 400, "user_id": 7})
    thr.add_user.assert_awaited_once()
    assert thr.add_user.await_args.args[0].id == 7


async def test_member_remove_dry_run_vs_live():
    guild, _c, _m, thr, _nt = make_guild()
    result = await thread_ops.member_remove(ctx_for(guild, True), {"thread_id": 400, "user_id": 7})
    assert result["planned"] is True
    thr.remove_user.assert_not_awaited()
    await thread_ops.member_remove(ctx_for(guild, False), {"thread_id": 400, "user_id": 7})
    thr.remove_user.assert_awaited_once()
    assert thr.remove_user.await_args.args[0].id == 7


async def test_member_info_read():
    guild, _c, _m, thr, _nt = make_guild()
    result = await thread_ops.member_info(ctx_for(guild, True), {"thread_id": 400, "user_id": 7})
    thr.fetch_member.assert_awaited_once_with(7)
    assert result == {"id": "7", "thread_id": "400", "joined_at": None}


async def test_members_list_read():
    guild, _c, _m, thr, _nt = make_guild()
    result = await thread_ops.members_list(ctx_for(guild, True), {"thread_id": 400})
    thr.fetch_members.assert_awaited_once()
    assert [m["id"] for m in result] == ["7", "8"]


async def test_delete_dry_run_vs_live():
    guild, _c, _m, thr, _nt = make_guild()
    result = await thread_ops.delete(ctx_for(guild, True), {"thread_id": 400})
    assert result["planned"] is True
    thr.delete.assert_not_awaited()
    result = await thread_ops.delete(ctx_for(guild, False), {"thread_id": 400})
    thr.delete.assert_awaited_once()
    assert result["deleted"] is True


async def test_resolve_thread_falls_back_to_get_channel():
    thr = make_thread()
    guild = SimpleNamespace(
        id=1,
        get_thread=lambda tid: None,
        get_channel=lambda cid: thr if cid == 400 else None,
    )
    result = await thread_ops.info(ctx_for(guild, True), {"thread_id": 400})
    assert result["id"] == "400"
