from claude_control.ops.registry import REGISTRY, load_all_handlers

EXPECTED_MUTATING = {
    "guild.edit", "guild.apply",
    "channel.create", "channel.edit", "channel.delete", "channel.move", "channel.clone", "channel.sync",
    "category.create", "category.edit", "category.delete", "category.move",
    "role.create", "role.edit", "role.delete", "role.move", "role.clone", "role.permissions_set",
    "member.ban", "member.unban", "member.kick", "member.timeout", "member.untimeout",
    "member.nick", "member.roles_add", "member.roles_remove", "member.roles_set",
    "member.voice_move", "member.voice_disconnect",
    "message.send", "message.edit", "message.delete", "message.purge",
    "message.pin", "message.unpin", "message.react",
    "permissions.channel_overwrite_set", "permissions.channel_overwrite_clear",
    "thread.create_forum_post",
    "emoji.create", "emoji.delete",
    "invite.create", "invite.delete",
    "webhook.create", "webhook.delete",
}

EXPECTED_READ = {
    "bot.ping", "bot.version", "bot.guilds", "bot.stats",
    "guild.info", "guild.snapshot", "guild.diff", "guild.audit_log",
    "channel.list", "channel.info",
    "category.list", "category.info", "category.children",
    "role.list", "role.info",
    "member.list", "member.search", "member.info",
    "message.history", "message.search",
    "permissions.channel_overwrites", "permissions.resolve_member", "permissions.resolve_role",
    "thread.list_active", "thread.list_archived", "thread.info", "thread.history",
    "emoji.list",
    "invite.list",
    "webhook.list",
}


def test_all_handlers_load():
    load_all_handlers()
    assert len(REGISTRY.ops()) == 75


def test_mutating_flags_match_plan():
    load_all_handlers()
    assert REGISTRY.mutating_ops() == EXPECTED_MUTATING


def test_read_ops_match_plan():
    load_all_handlers()
    read_ops = set(REGISTRY.ops()) - REGISTRY.mutating_ops()
    assert read_ops == EXPECTED_READ


def test_op_set_is_exactly_catalog():
    load_all_handlers()
    assert set(REGISTRY.ops()) == EXPECTED_MUTATING | EXPECTED_READ
