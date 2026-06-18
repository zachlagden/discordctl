# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-19

The op catalog grows from **75 to 179 operations**, turning discordctl into a near-complete
admin surface over the Discord API.

### Added

- **Rich messages** — `message.send` / `message.edit` (and `user.dm_send`, `webhook.execute`)
  now accept embeds, components (raw Discord button/select JSON), file attachments (base64),
  polls, replies (`message_reference` / `reply`), `sticker_ids`, `allowed_mentions`, `tts`, and
  message flags.
- **Bot presence** — `bot.presence_set` / `bot.presence_clear` / `bot.presence_get` for
  activity and status. Presence is ephemeral in-memory state and is lost on restart.
- **Threads** — full lifecycle: create (standard, from-message, forum post), edit, archive,
  lock, join/leave, member add/remove, member info, list active/archived, history, delete.
- **Scheduled events** — list, info, create, edit, delete, and interested users.
- **AutoMod** — list, info, create, edit, delete rules.
- **Stickers** — guild sticker CRUD plus global fetch and premium sticker packs.
- **Stage instances** — start, info, edit, end.
- **Soundboard** — list, info, create, edit, delete sounds.
- **Templates** — list, get, create, sync, edit, delete guild templates.
- **Voice state** — read voice state and set the bot's own or another member's voice state.
- **Webhook execution** — `webhook.execute` plus webhook message get/edit/delete and
  guild-wide / by-id webhook listing.
- **Expanded guild settings** — full `guild.edit`, member prune (count + execute), bans list /
  ban info / bulk ban, onboarding, welcome screen, widget, integrations, incident actions,
  preview, voice regions, and vanity URL.
- **Expanded channel settings** — full `channel.edit`, follow, clone, sync, voice status, and
  typing indicator.
- **Roles** — gradient (holographic) colours and role icons on create/edit, member counts,
  and role move/clone/permission-set.
- **Members** — role set, self edit, voice move / disconnect.
- **Messages** — get, bulk delete, crosspost, pins list, and full reaction management
  (list / remove / clear).
- **Polls** — end a poll and list voters per answer.
- **Emoji** — guild emoji edit plus full application (bot) emoji CRUD.
- **Invites** — fetch by code with counts/expiration.
- **Bot** — gateway info, profile edit, and leave-guild.

### Changed

- `AGENTS.md` §6 command reference rewritten as per-domain tables covering all 179 ops, with
  new dedicated sections on bot presence and rich messages.

## [0.1.0] - 2026-06-18

### Added

- Initial release: localhost HTTP command bus and the `dctl` CLI with 75 operations covering
  bot diagnostics, guild basics, channels, categories, roles, member moderation, basic
  messaging, permission overwrites, threads, emojis, invites, and webhooks.
- Dry-run-by-default mutation workflow (`--confirm`) with declarative snapshot → diff → apply.

[Unreleased]: https://github.com/zachlagden/discordctl/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/zachlagden/discordctl/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/zachlagden/discordctl/releases/tag/v0.1.0
