# claude-control

A control plane that lets Claude Code fully manage a Discord server as a bot. A persistent
discord.py daemon holds the gateway connection and exposes a **localhost-only HTTP command bus**;
a `dctl` CLI drives that bus over the shell, so Claude (or any local script) can ban/edit users,
manage roles, channels, categories, permissions, messages, threads, emojis, invites, and webhooks —
75 operations in all.

Every mutating operation is **dry-run by default** and requires an explicit `--confirm`; writes are
gated by a guild allowlist and a global kill switch, and every call is written to an append-only
audit log.

## Quick start

```bash
uv sync
cp .env.example .env
# Edit .env — set DISCORD_TOKEN, BUS_TOKEN, ALLOWED_GUILD_IDS, DEFAULT_GUILD_ID
docker compose up -d        # or: uv run python -m claude_control
```

Then drive it:

```bash
uv run dctl health
uv run dctl ops
uv run dctl op guild.info
uv run dctl op role.create --arg name=example            # dry-run (preview only)
uv run dctl op role.create --arg name=example --confirm  # executes
```

## Documentation

- Setup guide (portal intents, invite URL, `.env`): [`docs/SETUP.md`](docs/SETUP.md)
- Live smoke-test checklist: [`docs/SMOKE.md`](docs/SMOKE.md)
- Design spec & implementation plan: [`docs/superpowers/`](docs/superpowers/)
