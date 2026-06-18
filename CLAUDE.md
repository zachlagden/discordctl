# CLAUDE.md

This file provides context to Claude Code (claude.ai/code) when working with this repository.

## Project Overview

`discordctl` lets an agent (or any local script) fully manage a Discord server from the command line.
A persistent discord.py daemon holds the gateway connection and exposes a localhost-only HTTP "command
bus"; the `dctl` CLI drives that bus, exposing 75 operations across the whole Discord management surface
with dry-run-by-default mutations and an append-only audit log.

## Tech Stack

- Python 3.11+, managed with **uv** (never pip/poetry)
- discord.py 2.x (gateway daemon), aiohttp (control bus), pydantic v2 (schemas)
- pytest + pytest-asyncio (tests), ruff (lint + format)
- Docker + Docker Compose for deployment; Sentry for error tracking

## Project Structure

```
src/discordctl/
  __main__.py          # python -m discordctl -> runs the daemon
  config.py            # env-driven Config
  schemas.py           # OpRequest / OpResponse (pydantic)
  daemon/
    bot.py             # discord.py client; starts the bus on_ready
    server.py          # aiohttp control bus + dry-run gating + auth
  ops/
    registry.py        # @op decorator, Registry, BusContext, plan(), HandlerError
    lookup.py          # resolve guild/channel/role/member (+ guild allowlist)
    serialize.py       # discord object -> JSON-safe dicts
    audit.py           # append-only audit writer
    handlers/          # one module per domain (bot, guild, channel, role, member, ...)
  cli/dctl.py          # the dctl CLI
tests/                 # pytest suite (mirrors src + handlers/)
scripts/invite_url.py  # OAuth2 invite-URL generator
docs/                  # SETUP.md, SMOKE.md, and the design spec/plan
```

## Development

### Setup
```bash
uv sync
cp .env.example .env   # then fill DISCORD_TOKEN, BUS_TOKEN, ALLOWED_GUILD_IDS, DEFAULT_GUILD_ID
```

### Running
```bash
uv run python -m discordctl        # or: docker compose up -d
uv run dctl health                 # drive the bus
uv run dctl op guild.info
```

### Testing
```bash
uv run pytest
```

### Linting
```bash
uv run ruff check .
uv run ruff format --check .
```

## Common Patterns

- Handlers register via `@op("domain.action", mutating=...)`. Read ops return serialized data; mutating
  ops must check `ctx.dry_run` and return `plan(...)` (performing NO write) before any discord.py call.
- Entities are resolved through `ops/lookup.py`, which also enforces the `ALLOWED_GUILD_IDS` allowlist.
- The server derives effective dry-run purely from `confirm` + `WRITE_ENABLED`; the client's `dry_run`
  body field cannot force a live mutation.
- No inline comments; self-documenting names. Type hints on every function.
- The op catalog is pinned by `tests/handlers/test_handlers_smoke.py` (75 ops, 45 mutating) — keep it
  in sync when adding ops.

## Key Files

- `src/discordctl/daemon/server.py` — security boundary (loopback + bearer, gating, error mapping)
- `src/discordctl/ops/registry.py` — op registration + `BusContext` contract
- `src/discordctl/ops/handlers/guild_state.py` — declarative snapshot/diff/apply (most complex)

## Environment Variables

Loaded from `.env` (gitignored). Never commit real values.

| Variable | Purpose |
|----------|---------|
| `DISCORD_TOKEN` | Bot token (all privileged intents required) |
| `BUS_TOKEN` | 256-bit hex bearer token for the control bus |
| `BUS_HOST` / `BUS_PORT` | Bus bind address (must stay loopback) / port |
| `ALLOWED_GUILD_IDS` | Comma-separated guild allowlist (empty = disabled) |
| `DEFAULT_GUILD_ID` | Guild used when an op omits `guild_id` |
| `WRITE_ENABLED` | Global kill switch; `false` forces every mutation to dry-run |
| `AUDIT_PATH` | Path to the append-only audit log |
| `SENTRY_DSN` | Optional Sentry DSN |

## Notes

- Every mutating op is dry-run-by-default and needs `--confirm`; destructive ops (`message.purge` > 100,
  `guild.apply` deletions) additionally need `--yes-really`; the bot refuses to ban/kick the guild owner.
- See `docs/SETUP.md` for portal/intents/invite wiring and `docs/SMOKE.md` for a live verification run.
