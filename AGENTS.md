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
manage the guild, channels, categories, roles, members (ban/kick/timeout/roles/voice), messages,
permission overwrites, threads, emojis, invites, and webhooks — **75 operations** total.

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
uv run dctl ops                    # list all 75 ops and whether each mutates
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

## 6. Complete command reference (all 75 ops)

`M` = mutating (dry-run-by-default, needs `--confirm`). `R` = read-only.

### bot — diagnostics (R)
| Op | Args | Returns |
|----|------|---------|
| `bot.ping` | — | gateway latency (ms) |
| `bot.version` | — | discordctl version |
| `bot.guilds` | — | guilds the bot is in (id, name, member_count) |
| `bot.stats` | — | guild count + op count |

### guild
| Op | T | Args | Notes |
|----|---|------|-------|
| `guild.info` | R | — | name, owner, counts |
| `guild.snapshot` | R | — | full declarative state (roles, categories, channels) as JSON |
| `guild.diff` | R | `desired` | diff current vs a desired snapshot (`--arg desired=@snap.json`) |
| `guild.audit_log` | R | `limit?` | recent Discord audit-log entries |
| `guild.edit` | M | `name?`, `description?`, `reason?` | edit guild settings |
| `guild.apply` | M | `desired`, **`--yes-really` if it deletes** | apply a desired snapshot (see §7) |

### channel
| Op | T | Args | Notes |
|----|---|------|-------|
| `channel.list` | R | — | all channels |
| `channel.info` | R | `channel_id\|channel_name` | |
| `channel.create` | M | `name`, `type?`, `category_id?`, `topic?`, `nsfw?`, `reason?` | `type` ∈ text/voice/forum/stage/category (default text). `topic` rejected by voice/stage/category; `nsfw` rejected by category |
| `channel.edit` | M | `channel_id\|channel_name`, any of `name`/`topic`/`nsfw`/`slowmode_delay`/`position`, `reason?` | only whitelisted fields are applied |
| `channel.move` | M | `channel_id\|channel_name`, `position`, `reason?` | reorder |
| `channel.clone` | M | `channel_id\|channel_name`, `name?`, `reason?` | duplicate |
| `channel.sync` | M | `channel_id\|channel_name`, `reason?` | sync overwrites to parent category |
| `channel.delete` | M | `channel_id\|channel_name`, `reason?` | |

### category
| Op | T | Args | Notes |
|----|---|------|-------|
| `category.list` | R | — | |
| `category.info` | R | `category_id\|category_name` | |
| `category.children` | R | `category_id\|category_name` | channels under it |
| `category.create` | M | `name`, `reason?` | |
| `category.edit` | M | `category_id\|category_name`, `name?`, `position?`, `reason?` | |
| `category.move` | M | `category_id\|category_name`, `position`, `reason?` | |
| `category.delete` | M | `category_id\|category_name`, `reason?` | |

### role
| Op | T | Args | Notes |
|----|---|------|-------|
| `role.list` | R | — | |
| `role.info` | R | `role_id\|role_name` | |
| `role.create` | M | `name`, `colour?`, `permissions?`, `hoist?`, `mentionable?`, `reason?` | `colour` = hex string `#5865F2` or integer; `permissions` = integer bitfield |
| `role.edit` | M | `role_id\|role_name`, any of `name`/`hoist`/`mentionable`/`colour`, `reason?` | |
| `role.move` | M | `role_id\|role_name`, `position`, `reason?` | reorder (affects hierarchy) |
| `role.clone` | M | `role_id\|role_name`, `name?`, `reason?` | copy perms/colour/flags |
| `role.permissions_set` | M | `role_id\|role_name`, `permissions`, `reason?` | replace the role's permission bitfield |
| `role.delete` | M | `role_id\|role_name`, `reason?` | |

### member — moderation
| Op | T | Args | Notes |
|----|---|------|-------|
| `member.list` | R | `limit?` | cached members |
| `member.search` | R | `query?`, `limit?` | match name/display name |
| `member.info` | R | `user_id\|user_name` | includes presence `status`/`activity` |
| `member.ban` | M | `user_id`, `delete_message_seconds?`, `reason?` | numeric `user_id` only; refuses owner |
| `member.unban` | M | `user_id`, `reason?` | numeric `user_id` |
| `member.kick` | M | `user_id\|user_name`, `reason?` | refuses owner |
| `member.timeout` | M | `user_id\|user_name`, `seconds`, `reason?` | timed mute |
| `member.untimeout` | M | `user_id\|user_name`, `reason?` | clear timeout |
| `member.nick` | M | `user_id\|user_name`, `nick?`, `reason?` | omit `nick` to clear |
| `member.roles_add` | M | `user_id\|user_name`, `role_ids`, `reason?` | `role_ids` = JSON array |
| `member.roles_remove` | M | `user_id\|user_name`, `role_ids`, `reason?` | |
| `member.roles_set` | M | `user_id\|user_name`, `role_ids`, `reason?` | replaces all roles |
| `member.voice_move` | M | `user_id\|user_name`, `channel_id`, `reason?` | move between voice channels |
| `member.voice_disconnect` | M | `user_id\|user_name`, `reason?` | kick from voice |

### message
| Op | T | Args | Notes |
|----|---|------|-------|
| `message.history` | R | `channel_id\|channel_name`, `limit?` | recent messages |
| `message.search` | R | `channel_id\|channel_name`, `query?`, `limit?` | substring match on content |
| `message.send` | M | `channel_id\|channel_name`, `content` | |
| `message.edit` | M | `channel_id\|channel_name`, `message_id`, `content` | |
| `message.delete` | M | `channel_id\|channel_name`, `message_id` | |
| `message.purge` | M | `channel_id\|channel_name`, `limit`, **`--yes-really` if `limit` > 100** | bulk delete |
| `message.pin` | M | `channel_id\|channel_name`, `message_id`, `reason?` | |
| `message.unpin` | M | `channel_id\|channel_name`, `message_id`, `reason?` | |
| `message.react` | M | `channel_id\|channel_name`, `message_id`, `emoji` | unicode or `name:id` custom emoji |

### permissions — channel overwrites
| Op | T | Args | Notes |
|----|---|------|-------|
| `permissions.channel_overwrites` | R | `channel_id\|channel_name` | list all overwrites on a channel |
| `permissions.resolve_member` | R | `channel_id\|channel_name`, `user_id\|user_name` | effective perms for a member |
| `permissions.resolve_role` | R | `channel_id\|channel_name`, `role_id\|role_name` | effective perms for a role |
| `permissions.channel_overwrite_set` | M | `channel_id\|channel_name`, target (`role_id\|role_name` **or** `user_id`), `allow?`, `deny?`, `reason?` | `allow`/`deny` = JSON arrays of permission names, e.g. `--arg allow=["send_messages","view_channel"]` |
| `permissions.channel_overwrite_clear` | M | `channel_id\|channel_name`, target (`role_id\|role_name` **or** `user_id`), `reason?` | remove the overwrite |

### thread
| Op | T | Args | Notes |
|----|---|------|-------|
| `thread.list_active` | R | — | active threads in the guild |
| `thread.list_archived` | R | `channel_id\|channel_name`, `limit?` | archived threads under a channel |
| `thread.info` | R | `thread_id` | |
| `thread.history` | R | `thread_id`, `limit?` | messages in a thread |
| `thread.create_forum_post` | M | `channel_id\|channel_name` (a forum), `name`, `content` | new forum post |

### emoji
| Op | T | Args | Notes |
|----|---|------|-------|
| `emoji.list` | R | — | |
| `emoji.create` | M | `name`, `image_b64`, `reason?` | `image_b64` = base64-encoded image bytes |
| `emoji.delete` | M | `emoji_id`, `reason?` | |

### invite
| Op | T | Args | Notes |
|----|---|------|-------|
| `invite.list` | R | — | |
| `invite.create` | M | `channel_id\|channel_name`, `max_age?`, `max_uses?`, `reason?` | `0` = never expire / unlimited |
| `invite.delete` | M | `code`, `reason?` | invite code string |

### webhook
| Op | T | Args | Notes |
|----|---|------|-------|
| `webhook.list` | R | `channel_id\|channel_name` | |
| `webhook.create` | M | `channel_id\|channel_name`, `name`, `reason?` | |
| `webhook.delete` | M | `channel_id\|channel_name`, `webhook_id`, `reason?` | |

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

1. **Discover every page** from the sitemap (≈150 pages):
   <https://docs.discord.com/sitemap.xml> — each `<loc>` is a page URL. (There's also an
   LLM-oriented index at <https://docs.discord.com/llms.txt>.)
2. **Read any page as Markdown** by appending `.md` to its URL. For example, the page
   `https://docs.discord.com/developers/components/using-message-components`
   becomes a clean Markdown document at
   `https://docs.discord.com/developers/components/using-message-components.md`.

So the workflow is: pull `sitemap.xml` → pick the relevant page URL → fetch that URL **+ `.md`** →
read the Markdown. Use it to confirm permission flag names, limits, and payload shapes before issuing
a mutation.
