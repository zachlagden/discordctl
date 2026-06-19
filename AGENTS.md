# AGENTS.md — operating discordctl

This guide is for an **AI agent that will use `discordctl` to manage a Discord server** on a
user's behalf. It explains how the tool works, every command and its arguments, the safety model,
and how to walk the user through first-time setup.

> If you are instead an agent working **on the discordctl codebase**, read `CLAUDE.md` instead.

---

## 1. What you are driving

`discordctl` is a persistent discord.py daemon that holds a gateway connection and exposes a
**localhost-only HTTP command bus**. You drive it through the **`dctl` CLI** over the shell. One
command per action; JSON in, JSON out. You can do essentially anything a server admin can:
manage the guild, channels, categories, roles, members (ban/kick/timeout/roles/voice), rich messages
(embeds, components, files, polls), bot presence, threads, scheduled events, automod, stickers, stage
instances, permission overwrites, emojis, invites, webhooks, voice state, soundboard, and templates —
**179 operations** total.

You are acting as a server administrator. Treat every mutation as consequential.

---

## 2. Golden rules (read before acting)

1. **Dry-run first, always.** Every mutating op is **dry-run by default**. Run it *without*
   `--confirm` first to preview the plan, show/consider it, then re-run *with* `--confirm` to
   execute. Never pass `--confirm` on the first attempt at a destructive change.
2. **Confirm intent for destructive actions.** Bans, kicks, deletes, purges, role/permission
   changes, and `guild.apply` change real users' experience. Surface what will happen and get the
   user's go-ahead before the confirmed run unless they've told you to proceed.
3. **Destructive guardrails need `--yes-really`.** `message.purge` of more than 100 messages and
   `guild.apply` operations that delete entities require `--yes-really` *in addition to* `--confirm`.
4. **The guild owner cannot be banned or kicked** — the daemon refuses (`code: refused`).
5. **Stay inside the allowlist.** Ops only work on guilds in `ALLOWED_GUILD_IDS`. Other guilds
   return `code: forbidden`.
6. **Respect the kill switch.** If `WRITE_ENABLED=false`, *every* mutation is forced to dry-run even
   with `--confirm`. If your confirmed mutation still returns `dry_run: true`, the kill switch is on.
7. **Prefer IDs over names.** Name lookups can be ambiguous (`code: ambiguous`) or miss uncached
   members (`code: not_found`). Use numeric IDs when you have them.
8. **Snapshot before sweeping changes.** Run `guild.snapshot` and save the JSON before large
   restructures so you can diff/restore.

Every call (including dry-runs and failures) is written to an append-only audit log (`AUDIT_PATH`,
default `./audit.jsonl`).

---

## 3. How to invoke

### Commands

```bash
uv run dctl health                 # is the bus up?  -> {"ok":true,"data":{"status":"ready"}}
uv run dctl ops                    # list all 179 ops and whether each mutates
uv run dctl describe <op>          # show one op's name + mutating flag
uv run dctl op <name> [--arg k=v]... [--confirm] [--yes-really] [--json]
```

(If `dctl` is installed on PATH you can drop `uv run`. The two are equivalent.)

### Passing arguments — `--arg key=value`

Repeat `--arg` once per argument. Values are coerced automatically:

| You write | Parsed as |
|-----------|-----------|
| `--arg limit=50` | integer `50` |
| `--arg nsfw=true` | boolean `true` |
| `--arg name=general` | string `"general"` |
| `--arg role_ids=[111,222]` | JSON array `[111, 222]` |
| `--arg desired={...}` | JSON object |
| `--arg desired=@snapshot.json` | contents of the file (parsed as JSON if valid) |
| `--arg reason="spam wave"` | string with spaces (quote it in the shell) |

Use `@file.json` for anything large (a `guild.apply` desired-state snapshot, a long message body).

### Flags

- `--confirm` — execute a mutation for real (without it, mutations only preview). Sets `dry_run=false`.
- `--yes-really` — required for over-threshold destructive ops (see rule 3).
- `--json` — print the raw JSON response (use this when you want to parse it programmatically;
  omit it for pretty-printed output).

### Response shape

```json
{
  "ok": true,
  "data": <result or dry-run plan>,
  "error": null,
  "request_id": "req_…",
  "dry_run": true,        // present for mutating ops; null for reads
  "must_confirm": true    // present only when a mutation was withheld pending --confirm
}
```

- A **dry-run** mutation returns `data: {"planned": true, "action": "...", ...}` with `dry_run: true`
  and `must_confirm: true`, and changes nothing.
- On failure, `ok: false` and `error: {"message": "...", "code": "..."}`.

### Exit codes

`0` success · `1` op error (`ok:false`) · `2` usage error · `3` cannot reach the bus.

### Error codes you will see

| `code` | Meaning | What to do |
|--------|---------|------------|
| `bad_args` | Missing/invalid argument | Fix the args; check this guide's reference |
| `not_found` | Entity/guild not found | Verify the ID; ensure the bot is in the guild |
| `ambiguous` | A name matched multiple entities | Pass the numeric ID instead |
| `forbidden` | Guild not in the allowlist | Use an allowlisted guild |
| `refused` | Blocked by a guardrail (e.g. owner ban) | Don't retry; it's intentional |
| `needs_yes_really` | Over-threshold destructive op | Add `--yes-really` (only if truly intended) |
| `http_error` | Discord API error (status surfaced) | Read the message; `retry_after` is included on 429 |

---

## 4. The core workflow (dry-run → confirm)

```bash
# 1. Preview — nothing happens
uv run dctl op member.ban --arg user_id=123456789012345678 --arg reason="raid account"
#   -> {"ok":true,"data":{"planned":true,"action":"ban",...},"dry_run":true,"must_confirm":true}

# 2. Execute — after you've confirmed intent with the user
uv run dctl op member.ban --arg user_id=123456789012345678 --arg reason="raid account" --confirm
#   -> {"ok":true,"data":{"banned":"123456789012345678"},"dry_run":false}
```

Read ops never need `--confirm`:

```bash
uv run dctl op member.search --arg query=alex --arg limit=10
uv run dctl op channel.list
```

---

## 5. Common arguments

These apply to most ops, so they aren't repeated in every row below:

- **`guild_id`** *(optional everywhere)* — the target guild. Omit it to use `DEFAULT_GUILD_ID`.
  Pass it explicitly when managing more than one server.
- **`reason`** *(optional on most mutations)* — written to Discord's audit log as the action reason.
- **Entity selectors** — where a table says `channel_id|channel_name` (etc.), pass **one** of them.
  IDs are exact; names must be unique or you get `ambiguous`.

---

## 6. Complete command reference (all 179 ops)

`M` = mutating (dry-run-by-default, needs `--confirm`). `R` = read-only. `guild_id` is optional
everywhere (defaults to `DEFAULT_GUILD_ID`) and `reason?` applies to most mutations — neither is
repeated below. Ops added in v2 (beyond the original 75) are marked **[new]**.

### bot — diagnostics & presence
| Op | T | Args | Notes |
|----|---|------|-------|
| `bot.ping` | R | — | gateway latency (ms) |
| `bot.version` | R | — | discordctl version |
| `bot.guilds` | R | — | guilds the bot is in |
| `bot.stats` | R | — | guild + op counts |
| `bot.gateway` | R | — | gateway/session info **[new]** |
| `bot.presence_set` | M | `type?`, `name?`, `status?`, `url?` | ephemeral, lost on restart **[new]** |
| `bot.presence_clear` | M | — | clears activity **[new]** |
| `bot.presence_get` | R | — | reads in-memory presence **[new]** |
| `bot.profile_edit` | M | `username?`, `avatar_b64?` | edit the bot user **[new]** |
| `bot.leave_guild` | M | `guild_id`, **`--yes-really`** | destructive **[new]** |

See **Bot presence** below for the ephemeral-state caveat.

### user
| Op | T | Args | Notes |
|----|---|------|-------|
| `user.me` | R | — | the bot user |
| `user.get` | R | `user_id` | any user by id |
| `user.dm_send` | M | `user_id`, rich-message args | DM with full rich surface **[new]** |

### guild
| Op | T | Args | Notes |
|----|---|------|-------|
| `guild.info` | R | — | name, owner, counts |
| `guild.preview` | R | — | discovery preview **[new]** |
| `guild.audit_log` | R | `limit?` | recent audit-log entries |
| `guild.vanity_url` | R | — | vanity invite **[new]** |
| `guild.voice_regions` | R | — | available regions **[new]** |
| `guild.edit` | M | any of `name`/`description`/`icon`/`banner`/`splash`/`discovery_splash` (each also accepts `<field>_b64`)/`vanity_code`/`afk_channel`/`afk_timeout`/`system_channel`/`rules_channel`/`public_updates_channel`/`safety_alerts_channel`/`widget_channel` (channel fields also accept `<field>_id`)/`community`/`discoverable`/`invites_disabled`/`widget_enabled`/`raid_alerts_disabled`/`premium_progress_bar_enabled`/`verification_level`/`default_notifications`(`default_message_notifications`)/`explicit_content_filter`/`mfa_level`/`preferred_locale`/`system_channel_flags`/`invites_disabled_until`/`dms_disabled_until` | full Modify-Guild surface incl. `community` toggle (excludes `owner`); enabling `community` needs `rules_channel`+`public_updates_channel` **[new]** |
| `guild.prune_count` | R | `days?`, `role_ids?` | dry estimate **[new]** |
| `guild.prune` | M | `days?`, `role_ids?`, `compute_prune_count?` | remove inactive members **[new]** |
| `guild.onboarding_get` | R | — | **[new]** |
| `guild.onboarding_edit` | M | `enabled?`, `mode?`, `default_channel_ids?` | **[new]** |
| `guild.welcome_screen_get` | R | — | **[new]** |
| `guild.welcome_screen_edit` | M | `description?`, `enabled?`, `welcome_channels?` | **[new]** |
| `guild.widget_get` | R | — | **[new]** |
| `guild.widget_edit` | M | `enabled?`, `channel_id?` | **[new]** |
| `guild.integrations_list` | R | — | **[new]** |
| `guild.integration_delete` | M | `integration_id` | **[new]** |
| `guild.incident_actions_set` | M | `invites_disabled_until?` and/or `dms_disabled_until?` | one required **[new]** |
| `guild.snapshot` | R | — | full declarative state as JSON (see §7) |
| `guild.diff` | R | `desired` | diff current vs a desired snapshot |
| `guild.apply` | M | `desired`, **`--yes-really` if it deletes** | apply a desired snapshot (see §7) |

### channel
| Op | T | Args | Notes |
|----|---|------|-------|
| `channel.list` | R | — | all channels |
| `channel.info` | R | `channel_id\|channel_name` | |
| `channel.create` | M | `name`, `type?`, `category_id?`, plus type-specific (`topic?`, `nsfw?`, `slowmode_delay?`, `bitrate?`, `user_limit?`, `rtc_region?`, `available_tags?`, `permission_overwrites?` …) | `type` ∈ text/voice/forum/stage/category |
| `channel.edit` | M | `channel_id\|channel_name`, any of `name`/`topic`/`nsfw`/`slowmode_delay`/`position`/`bitrate`/`user_limit`/`rtc_region`/`video_quality_mode`/`available_tags`/`default_*`/`flags`/`category_id`/`permission_overwrites`/`sync_permissions` | expanded settings **[new]** |
| `channel.move` | M | `channel_id\|channel_name`, `position` | reorder |
| `channel.clone` | M | `channel_id\|channel_name`, `name?` | duplicate |
| `channel.sync` | M | `channel_id\|channel_name` | sync overwrites to parent category |
| `channel.follow` | M | `channel_id\|channel_name`, `target_channel_id` | crosspost an announcement channel **[new]** |
| `channel.voice_status_set` | M | `channel_id\|channel_name`, `status?` | set voice channel status **[new]** |
| `channel.typing` | M | `channel_id\|channel_name` | trigger typing indicator **[new]** |
| `channel.delete` | M | `channel_id\|channel_name` | |

### category
| Op | T | Args | Notes |
|----|---|------|-------|
| `category.list` | R | — | |
| `category.info` | R | `category_id\|category_name` | |
| `category.children` | R | `category_id\|category_name` | channels under it |
| `category.create` | M | `name` | |
| `category.edit` | M | `category_id\|category_name`, `name?`, `position?` | |
| `category.move` | M | `category_id\|category_name`, `position` | |
| `category.delete` | M | `category_id\|category_name` | |

### role
| Op | T | Args | Notes |
|----|---|------|-------|
| `role.list` | R | — | |
| `role.info` | R | `role_id\|role_name` | |
| `role.member_counts` | R | — | members per role (cache-based) **[new]** |
| `role.create` | M | `name`, `colour?`, `permissions?`, `hoist?`, `mentionable?`, `icon?`, `unicode_emoji?`, `colors?` | `colors` = gradient holographic colours **[new]**; `icon` = role icon |
| `role.edit` | M | `role_id\|role_name`, any of `name`/`colour`/`permissions`/`hoist`/`mentionable`/`icon`/`unicode_emoji`/`colors`/`position` | gradient colours + icon + position **[new]** |
| `role.move` | M | `role_id\|role_name`, `position` | reorder (affects hierarchy) |
| `role.clone` | M | `role_id\|role_name`, `name?` | copy perms/colour/flags |
| `role.permissions_set` | M | `role_id\|role_name`, `permissions` | replace permission bitfield |
| `role.delete` | M | `role_id\|role_name` | |

### member — moderation
| Op | T | Args | Notes |
|----|---|------|-------|
| `member.list` | R | `limit?` | cached members |
| `member.search` | R | `query?`, `limit?` | match name/display name |
| `member.info` | R | `user_id\|user_name` | includes presence `status`/`activity` |
| `member.ban` | M | `user_id`, `delete_message_seconds?` | numeric id; refuses owner |
| `member.bans_list` | R | `limit?` | the ban list **[new]** |
| `member.ban_info` | R | `user_id` | single ban entry **[new]** |
| `member.bulk_ban` | M | `user_ids` (1..200) , `delete_message_seconds?` | **[new]** |
| `member.unban` | M | `user_id` | numeric id |
| `member.kick` | M | `user_id\|user_name` | refuses owner |
| `member.timeout` | M | `user_id\|user_name`, `seconds` | timed mute |
| `member.untimeout` | M | `user_id\|user_name` | clear timeout |
| `member.nick` | M | `user_id\|user_name`, `nick?` | omit `nick` to clear |
| `member.roles_add` | M | `user_id\|user_name`, `role_ids` | `role_ids` = JSON array |
| `member.roles_remove` | M | `user_id\|user_name`, `role_ids` | |
| `member.roles_set` | M | `user_id\|user_name`, `role_ids` | replaces all roles **[new]** |
| `member.self_edit` | M | `nick?` | edit the bot's own member **[new]** |
| `member.voice_move` | M | `user_id\|user_name`, `channel_id` | move between voice channels **[new]** |
| `member.voice_disconnect` | M | `user_id\|user_name` | kick from voice **[new]** |

### message
| Op | T | Args | Notes |
|----|---|------|-------|
| `message.history` | R | `channel_id\|channel_name`, `limit?` | recent messages |
| `message.search` | R | `channel_id\|channel_name`, `query?`, `limit?` | substring match on content |
| `message.get` | R | `channel_id\|channel_name`, `message_id` | single message |
| `message.send` | M | `channel_id\|channel_name`, rich-message args | embeds/components/files/poll/reply **[new]** |
| `message.edit` | M | `channel_id\|channel_name`, `message_id`, any of `content`/`embeds`/`components`/`allowed_mentions`/`flags` | **[new]** |
| `message.delete` | M | `channel_id\|channel_name`, `message_id` | |
| `message.bulk_delete` | M | `channel_id\|channel_name`, `message_ids` (2..100) | **[new]** |
| `message.purge` | M | `channel_id\|channel_name`, `limit`, **`--yes-really` if `limit` > 100** | bulk delete by count |
| `message.crosspost` | M | `channel_id\|channel_name`, `message_id` | publish announcement **[new]** |
| `message.pin` | M | `channel_id\|channel_name`, `message_id` | |
| `message.unpin` | M | `channel_id\|channel_name`, `message_id` | |
| `message.pins_list` | R | `channel_id\|channel_name` | **[new]** |
| `message.react` | M | `channel_id\|channel_name`, `message_id`, `emoji` | unicode or `name:id` custom |
| `message.reactions_list` | R | `channel_id\|channel_name`, `message_id`, `emoji`, `limit?` | who reacted **[new]** |
| `message.reaction_remove` | M | `channel_id\|channel_name`, `message_id`, `emoji`, `user_id?` | **[new]** |
| `message.reactions_clear` | M | `channel_id\|channel_name`, `message_id`, `emoji?` | clear one or all **[new]** |

See **Rich messages** below for the full `send`/`edit` argument surface.

### poll
| Op | T | Args | Notes |
|----|---|------|-------|
| `poll.end` | M | `channel_id\|channel_name`, `message_id` | message must carry a poll **[new]** |
| `poll.voters` | R | `channel_id\|channel_name`, `message_id`, `answer_id` | who voted for an answer **[new]** |

### permissions — channel overwrites
| Op | T | Args | Notes |
|----|---|------|-------|
| `permissions.channel_overwrites` | R | `channel_id\|channel_name` | list all overwrites on a channel |
| `permissions.resolve_member` | R | `channel_id\|channel_name`, `user_id\|user_name` | effective perms for a member |
| `permissions.resolve_role` | R | `channel_id\|channel_name`, `role_id\|role_name` | effective perms for a role |
| `permissions.channel_overwrite_set` | M | `channel_id\|channel_name`, target (`role_id\|role_name` **or** `user_id`), `allow?`, `deny?` | `allow`/`deny` = JSON arrays of permission names |
| `permissions.channel_overwrite_clear` | M | `channel_id\|channel_name`, target (`role_id\|role_name` **or** `user_id`) | remove the overwrite |

### thread
| Op | T | Args | Notes |
|----|---|------|-------|
| `thread.list_active` | R | — | active threads in the guild |
| `thread.list_archived` | R | `channel_id\|channel_name`, `limit?`, `type?` | `type` ∈ public/private/joined **[new]** |
| `thread.info` | R | `thread_id` | **[new]** |
| `thread.history` | R | `thread_id`, `limit?` | messages in a thread **[new]** |
| `thread.create` | M | `channel_id\|channel_name`, `name`, `type?`, `auto_archive_duration?`, `invitable?`, `slowmode_delay?` | **[new]** |
| `thread.create_from_message` | M | `channel_id\|channel_name`, `message_id`, `name`, `auto_archive_duration?` | **[new]** |
| `thread.create_forum_post` | M | `channel_id\|channel_name` (a forum), `name`, `content` | new forum post |
| `thread.edit` | M | `thread_id`, any of `name`/`archived`/`locked`/`auto_archive_duration`/`slowmode_delay`/`invitable`/`applied_tags` | **[new]** |
| `thread.archive` | M | `thread_id` | **[new]** |
| `thread.lock` | M | `thread_id` | **[new]** |
| `thread.join` | M | `thread_id` | **[new]** |
| `thread.leave` | M | `thread_id` | **[new]** |
| `thread.member_add` | M | `thread_id`, `user_id` | **[new]** |
| `thread.member_remove` | M | `thread_id`, `user_id` | **[new]** |
| `thread.member_info` | R | `thread_id`, `user_id` | **[new]** |
| `thread.members_list` | R | `thread_id` | **[new]** |
| `thread.delete` | M | `thread_id` | **[new]** |

### scheduled-event
| Op | T | Args | Notes |
|----|---|------|-------|
| `event.list` | R | — | **[new]** |
| `event.info` | R | `event_id` | **[new]** |
| `event.create` | M | `name`, `entity_type`, `start_time`, plus `channel_id?`/`location?`/`end_time?`/`description?`/`privacy_level?`/`image_b64?` | external needs `location`+`end_time` **[new]** |
| `event.edit` | M | `event_id`, any of `name`/`description`/`location`/`start_time`/`end_time`/`channel_id`/`entity_type`/`privacy_level`/`status` | **[new]** |
| `event.delete` | M | `event_id` | **[new]** |
| `event.users` | R | `event_id`, `limit?` | interested users **[new]** |

### automod
| Op | T | Args | Notes |
|----|---|------|-------|
| `automod.list` | R | — | **[new]** |
| `automod.info` | R | `rule_id` | **[new]** |
| `automod.create` | M | `name`, `event_type`, `trigger_type`, plus `trigger_metadata?`/`actions?`/`enabled?`/`exempt_roles?`/`exempt_channels?` | **[new]** |
| `automod.edit` | M | `rule_id`, any of `name`/`event_type`/`trigger_type`/`trigger_metadata`/`actions`/`enabled`/`exempt_roles`/`exempt_channels` | **[new]** |
| `automod.delete` | M | `rule_id` | **[new]** |

### sticker
| Op | T | Args | Notes |
|----|---|------|-------|
| `sticker.list` | R | — | guild stickers **[new]** |
| `sticker.info` | R | `sticker_id` | **[new]** |
| `sticker.get` | R | `sticker_id` | global fetch **[new]** |
| `sticker.packs` | R | — | premium sticker packs **[new]** |
| `sticker.create` | M | `name`, `emoji`, `file_b64`, `description?` | **[new]** |
| `sticker.edit` | M | `sticker_id`, any of `name`/`description`/`emoji` | **[new]** |
| `sticker.delete` | M | `sticker_id` | **[new]** |

### stage
| Op | T | Args | Notes |
|----|---|------|-------|
| `stage.create` | M | `channel_id\|channel_name` (a stage), `topic`, `privacy_level?`, `send_start_notification?`, `scheduled_event_id?` | starts a stage instance **[new]** |
| `stage.info` | R | `channel_id\|channel_name` | **[new]** |
| `stage.edit` | M | `channel_id\|channel_name`, `topic?`, `privacy_level?` | **[new]** |
| `stage.delete` | M | `channel_id\|channel_name` | ends the stage **[new]** |

### emoji
| Op | T | Args | Notes |
|----|---|------|-------|
| `emoji.list` | R | — | guild emojis |
| `emoji.info` | R | `emoji_id` | |
| `emoji.create` | M | `name`, `image_b64` | base64 image bytes |
| `emoji.edit` | M | `emoji_id`, `name?`, `roles?` | **[new]** |
| `emoji.delete` | M | `emoji_id` | |
| `emoji.app_list` | R | — | application (bot) emojis **[new]** |
| `emoji.app_info` | R | `emoji_id` | **[new]** |
| `emoji.app_create` | M | `name`, `image_b64` | **[new]** |
| `emoji.app_edit` | M | `emoji_id`, `name` | **[new]** |
| `emoji.app_delete` | M | `emoji_id` | **[new]** |

### invite
| Op | T | Args | Notes |
|----|---|------|-------|
| `invite.list` | R | — | guild invites |
| `invite.list_guild` | R | — | alias of `invite.list` **[new]** |
| `invite.info` | R | `code`, `with_counts?`, `with_expiration?` | global fetch by code **[new]** |
| `invite.create` | M | `channel_id\|channel_name`, `max_age?`, `max_uses?`, `temporary?`, `unique?`, `target_type?`, `target_user_id?` | `0` = never expire / unlimited |
| `invite.delete` | M | `code` | invite code string |

### webhook
| Op | T | Args | Notes |
|----|---|------|-------|
| `webhook.list` | R | `channel_id\|channel_name` | |
| `webhook.guild_list` | R | — | all webhooks in the guild **[new]** |
| `webhook.info` | R | `webhook_id` | **[new]** |
| `webhook.create` | M | `channel_id\|channel_name`, `name` | |
| `webhook.edit` | M | `webhook_id`, `name?`, `channel_id?` | **[new]** |
| `webhook.execute` | M | `webhook_id`, `content?`, `embeds?`, `files?`, `username?`, `avatar_url?`, `thread_id?`, `tts?` | post as the webhook; components rejected **[new]** |
| `webhook.message_get` | R | `webhook_id`, `message_id`, `thread_id?` | **[new]** |
| `webhook.message_edit` | M | `webhook_id`, `message_id`, `content?`, `embeds?`, `allowed_mentions?`, `thread_id?` | **[new]** |
| `webhook.message_delete` | M | `webhook_id`, `message_id`, `thread_id?` | **[new]** |
| `webhook.delete` | M | `channel_id\|channel_name`, `webhook_id` | |

### voice
| Op | T | Args | Notes |
|----|---|------|-------|
| `voice.state_get` | R | `user_id?` | defaults to the bot **[new]** |
| `voice.state_self_set` | M | `channel_id?` and/or `suppress?`/`request_to_speak?` | the bot's own voice state **[new]** |
| `voice.state_set` | M | `user_id`, `channel_id?`, `suppress?` | another member's voice state **[new]** |

### soundboard
| Op | T | Args | Notes |
|----|---|------|-------|
| `soundboard.list` | R | `include_default?` | **[new]** |
| `soundboard.info` | R | `sound_id` | **[new]** |
| `soundboard.create` | M | `name`, `sound_b64`, `volume?`, `emoji?` | **[new]** |
| `soundboard.edit` | M | `sound_id`, any of `name`/`volume`/`emoji` | **[new]** |
| `soundboard.delete` | M | `sound_id` | **[new]** |

### template
| Op | T | Args | Notes |
|----|---|------|-------|
| `template.list` | R | — | guild templates **[new]** |
| `template.get` | R | `code` | global fetch by code **[new]** |
| `template.create` | M | `name`, `description?` | snapshot the guild **[new]** |
| `template.sync` | M | `code` | resync to current state **[new]** |
| `template.edit` | M | `code`, `name?`, `description?` | **[new]** |
| `template.delete` | M | `code` | **[new]** |

---

### Bot presence

Presence is **ephemeral process state**, not a Discord setting — it is held in memory by the running
bot and **lost on restart**, never persisted.

- `bot.presence_set` — `type` (playing/streaming/listening/watching/competing), `name` (activity
  text), `status` (online/idle/dnd/invisible), `url` (only meaningful for `streaming`). All optional;
  pass what you want to change.
- `bot.presence_clear` — clears the activity back to none.
- `bot.presence_get` — returns the presence the bot currently holds in memory.

### Rich messages

`message.send` and `message.edit` (and `user.dm_send`, `webhook.execute`) accept a full rich payload,
not just `content`. Supported keys:

- **`content`** — plain text.
- **`embeds`** — JSON array of raw Discord embed objects (max 10).
- **`components`** — JSON array of raw Discord component rows (buttons, selects). `send`/`edit` only —
  `webhook.execute` rejects components.
- **`files`** — JSON array of `{"filename": ..., "data": <base64>}` attachments.
- **`poll`** — `{"question": ..., "answers": [...], "duration_hours": ..., "multiple": false}`.
- **`message_reference`** or **`reply`** — reply to a message (`reply` =
  `{"message_id": ..., "channel_id"?: ..., "fail_if_not_exists"?: ...}`).
- **`sticker_ids`** — JSON array of sticker ids to send.
- **`allowed_mentions`** — control which mentions ping (`{"users": [...], "roles": [...],
  "everyone": false}`).
- **`tts`**, **`silent`** (suppress notifications), **`suppress_embeds`**, and **`flags`** (edit only).

Pass complex args from files with `--arg key=@file.json`. Example — an embed plus a button row:

```bash
# e.json — [ { "title": "Release v0.2.0", "description": "179 ops now live", "color": 5793266 } ]
# c.json — [ { "type": 1, "components": [
#             { "type": 2, "style": 5, "label": "Changelog", "url": "https://example.com" } ] } ]
uv run dctl run message.send \
  --arg channel_name=announcements \
  --arg embeds=@e.json \
  --arg components=@c.json \
  --confirm
```

---

## 7. Declarative server management (snapshot → diff → apply)

For larger restructures, work declaratively instead of issuing many individual ops:

```bash
# Capture current state
uv run dctl op guild.snapshot --json > snapshot.json

# Edit snapshot.json to describe the desired roles/categories/channels, then preview the diff
uv run dctl op guild.diff --arg desired=@snapshot.json

# Apply it (dry-run first, then confirm; add --yes-really if the diff deletes anything)
uv run dctl op guild.apply --arg desired=@snapshot.json
uv run dctl op guild.apply --arg desired=@snapshot.json --confirm --yes-really
```

**v1 `guild.apply` is conservative:** it creates roles and categories, and deletes roles only under
`--yes-really`. Channel create/edit and finer role edits are **surfaced in the returned `changes`
for your review but not auto-applied** — make those with the individual `channel.*` / `role.*` ops.
Entities are matched by `name`, so two channels with the same name under different categories collapse
in the diff (informational only, since apply doesn't act on channels).

---

## 8. Helping the user set it up

If the daemon isn't running yet (or `dctl health` fails / returns exit code 3), walk the user through
this. You **cannot** do the Discord Developer Portal steps for them — give clear instructions and let
them act. Full detail is in `docs/SETUP.md`.

1. **Developer Portal → Bot tab.** Have them enable **all three privileged intents**: *Presence
   Intent*, *Server Members Intent*, *Message Content Intent*. (discordctl requests all intents; if
   any is off, the gateway connection is rejected with close code 4014.) Copy the **bot token** and
   the **Application (Client) ID** from *General Information*.
2. **`.env`** (in the project root, gitignored — never commit it):
   - `DISCORD_TOKEN=` the bot token.
   - `BUS_TOKEN=` a 256-bit hex secret — generate with
     `python -c "import secrets; print(secrets.token_hex(32))"`.
   - `ALLOWED_GUILD_IDS=` and `DEFAULT_GUILD_ID=` the target guild ID. **Strongly recommend setting
     the allowlist** — leaving `ALLOWED_GUILD_IDS` empty disables it, letting the bot act on *any*
     guild it's in. To get the ID: Discord → Settings → Advanced → enable Developer Mode → right-click
     the server → Copy Server ID.
   - Keep `BUS_HOST=127.0.0.1` (the bus trusts only loopback peers; never set `0.0.0.0`).
3. **Invite the bot.** Run `uv run python scripts/invite_url.py <CLIENT_ID>`, give the user the URL,
   and have them authorize it into the server (Administrator permission is requested).
4. **Start the daemon.** `uv run python -m discordctl` (or `docker compose up -d`). Confirm the log
   line `control bus on 127.0.0.1:8765 as <bot>` and that the bot shows online.
5. **Verify.** `uv run dctl health` → ready, then `uv run dctl ops` and a read like
   `uv run dctl op guild.info`. Do one dry-run → `--confirm` mutation to confirm writes work.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `dctl` exit code 3 / connection error | daemon not running, or wrong `BUS_*` | start `python -m discordctl`; check `BUS_TOKEN`/`BUS_HOST`/`BUS_PORT` in env |
| `unauthorized` (401) | `BUS_TOKEN` mismatch | ensure the CLI's `BUS_TOKEN` matches the daemon's |
| confirmed mutation still `dry_run: true` | `WRITE_ENABLED=false` kill switch | set `WRITE_ENABLED=true` and restart the daemon |
| `forbidden` on a valid guild | guild not in `ALLOWED_GUILD_IDS` | add it to the allowlist and restart |
| `ambiguous` | name matched several entities | pass the numeric ID |
| `not_found` on a member by name | member not in cache | pass `user_id`, or ensure Server Members intent is on |
| `http_error` with `retry_after` | Discord rate limit | wait `retry_after` seconds and retry |

When in doubt: `dctl ops` lists everything available, dry-run shows what *would* happen, and
`audit.jsonl` records what *did*.

---

## 10. Reference: Discord's official docs

discordctl is a thin layer over the Discord API, so Discord's own documentation is the source of
truth for semantics you need while operating it — exact **permission names** (for
`permissions.channel_overwrite_set` `allow`/`deny`), **rate limits**, **intents**, channel/role
**field constraints**, message **component/embed** structure, audit-log action types, and ID/snowflake
rules. Consult it whenever a value or limit is unclear rather than guessing.

**Docs home:** <https://docs.discord.com/>

**It's fully agent-readable** — no scraping HTML:

1. **Start from the LLM index:** <https://docs.discord.com/llms.txt> — a Markdown index of every
   page (~150) with a one-line description and a **direct link to that page's `.md` version**. Skim
   it to find the page you need, then fetch the `.md` link it gives you.
2. **Any page URL → Markdown:** append `.md` to a docs page URL to read it as Markdown — e.g.
   `https://docs.discord.com/developers/components/using-message-components` →
   `…/using-message-components.md`. (Handy when you have a page link from elsewhere; the entries in
   `llms.txt` already point straight at the `.md` files.)

So the workflow is: read `llms.txt` → pick the relevant page's `.md` link → read the Markdown. Use it
to confirm permission flag names, limits, and payload shapes before issuing a mutation.
