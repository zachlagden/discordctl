<div align="center">

# discordctl

**Control a Discord server from the command line — full, bot-driven server management with dry-run-by-default safety.**

[![License](https://img.shields.io/github/license/zachlagden/discordctl?style=flat-square)](LICENCE)
[![Stars](https://img.shields.io/github/stars/zachlagden/discordctl?style=flat-square)](https://github.com/zachlagden/discordctl/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/zachlagden/discordctl?style=flat-square)](https://github.com/zachlagden/discordctl/commits/main)
[![Issues](https://img.shields.io/github/issues/zachlagden/discordctl?style=flat-square)](https://github.com/zachlagden/discordctl/issues)

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.x-5865F2?style=flat-square&logo=discord&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-DE5FE9?style=flat-square&logo=astral&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)

[Setup](docs/SETUP.md) · [Live smoke test](docs/SMOKE.md) · [Report Bug](https://github.com/zachlagden/discordctl/issues) · [Request Feature](https://github.com/zachlagden/discordctl/issues)

</div>

---

## What is discordctl?

`discordctl` turns a Discord bot into a scriptable command-line control plane for your server. A
persistent [discord.py](https://discordpy.readthedocs.io/) daemon holds the gateway connection and
exposes a **localhost-only HTTP command bus**; the `dctl` CLI drives that bus over the shell — so you
(or an automation, or an AI coding agent) can ban and edit members, manage roles, channels, categories,
permissions, messages, threads, emojis, invites, and webhooks. **75 operations** in all, covering the
whole management surface.

It was built to let an AI agent administer a server safely, so safety is the headline: **every mutating
operation is dry-run by default** and requires an explicit `--confirm`, writes are bounded by a guild
allowlist and a global kill switch, and every call is appended to an audit log.

---

## Features

| Feature | Description |
| --- | --- |
| **75 operations** | Guild, channel, category, role, member, message, permissions, thread, emoji, invite, and webhook management — driven as `dctl op <name>`. |
| **Dry-run by default** | Every mutation previews what it *would* do and changes nothing until you pass `--confirm`. The client cannot bypass this. |
| **Guarded & auditable** | Guild allowlist, `WRITE_ENABLED` kill switch, owner-ban refusal, `--yes-really` for destructive ops, and an append-only JSONL audit log of every call. |
| **Declarative state** | `guild.snapshot` → `guild.diff` → `guild.apply`: capture the server to JSON, edit it, apply the difference. |
| **Localhost-only bus** | The control bus binds `127.0.0.1`, trusts only loopback peers, and authenticates every request with a constant-time bearer check. |

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/zachlagden/discordctl.git
cd discordctl
uv sync
```

### 2. Configure

```bash
cp .env.example .env
# Set DISCORD_TOKEN, BUS_TOKEN, ALLOWED_GUILD_IDS, DEFAULT_GUILD_ID
```

Generate the bot invite URL and authorize it into your server (see [docs/SETUP.md](docs/SETUP.md) for
the full walkthrough, including the required privileged intents):

```bash
uv run python scripts/invite_url.py <CLIENT_ID>
```

### 3. Run & drive it

```bash
uv run python -m discordctl                               # or: docker compose up -d

uv run dctl health
uv run dctl ops
uv run dctl op guild.info
uv run dctl op role.create --arg name=example             # dry-run (preview only)
uv run dctl op role.create --arg name=example --confirm   # executes
```

---

## How it works

```
you / a script / an agent
        │  shell
        ▼
      dctl  ──HTTP POST /v1/op (bearer, 127.0.0.1)──►  control bus (aiohttp)
        ▲                                                   │
        │  JSON                                             ▼
        └──────────────────────────────────────  op registry → handler → discord.py
                                                            │
                                                            ▼
                                                       Discord API
```

The daemon stays connected to the gateway (warm cache, bot shows online). `dctl` is stateless and talks
to the bus over loopback. For mutating ops the **server** decides the effective dry-run state from
`confirm` + `WRITE_ENABLED` — a crafted request body can't force a live write.

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| **Gateway daemon** | Python 3.11+, discord.py 2.x |
| **Control bus** | aiohttp (localhost), pydantic v2 |
| **CLI** | `dctl` (stdlib argparse + urllib) |
| **Tests / quality** | pytest, pytest-asyncio, ruff |
| **Deploy / observability** | Docker, Docker Compose, Sentry |

---

## Project Structure

```
src/discordctl/
├── __main__.py        # python -m discordctl -> runs the daemon
├── config.py          # env-driven configuration
├── schemas.py         # OpRequest / OpResponse
├── daemon/            # discord.py client + aiohttp control bus
├── ops/
│   ├── registry.py    # @op decorator, BusContext, dry-run plan()
│   ├── lookup.py      # entity resolution + guild allowlist
│   ├── serialize.py   # discord objects -> JSON
│   ├── audit.py       # append-only audit writer
│   └── handlers/      # one module per domain (75 ops)
└── cli/dctl.py        # the CLI
docs/                  # SETUP.md, SMOKE.md, design spec & plan
```

---

## Configuration

Loaded from `.env` (gitignored — never commit real values).

| Variable | Purpose |
| --- | --- |
| `DISCORD_TOKEN` | Bot token (all privileged intents required) |
| `BUS_TOKEN` | 256-bit hex bearer token for the control bus |
| `BUS_HOST` / `BUS_PORT` | Bus bind address (keep loopback) / port |
| `ALLOWED_GUILD_IDS` | Comma-separated guild allowlist (empty disables it) |
| `DEFAULT_GUILD_ID` | Guild used when an op omits `guild_id` |
| `WRITE_ENABLED` | Global kill switch; `false` forces every mutation to dry-run |
| `AUDIT_PATH` | Path to the append-only audit log |
| `SENTRY_DSN` | Optional Sentry DSN |

---

## Star History

<a href="https://star-history.com/#zachlagden/discordctl&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=zachlagden/discordctl&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=zachlagden/discordctl&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=zachlagden/discordctl&type=Date" />
 </picture>
</a>

---

## Support

If this project is useful to you, consider supporting development:

<a href="https://github.com/sponsors/zachlagden">
  <img src="https://img.shields.io/badge/Sponsor_on_GitHub-ea4aaa?style=for-the-badge&logo=github&logoColor=white" alt="Sponsor on GitHub" />
</a>

---

## License

This project is licensed under the MIT License — see the [LICENCE](LICENCE) file for details.

---

<div align="center">

**[Report Bug](https://github.com/zachlagden/discordctl/issues)** · **[Request Feature](https://github.com/zachlagden/discordctl/issues)**

Made by [Zach Lagden](https://github.com/zachlagden)

</div>
