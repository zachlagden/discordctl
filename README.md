# claude-control

A Discord bot that bridges Discord commands to a Claude Code daemon running on the host machine,
enabling Claude Code to be controlled from a Discord channel.

## Quick start

```bash
uv sync
cp .env.example .env
# Edit .env — set DISCORD_TOKEN, BUS_TOKEN, guild IDs, etc.
docker compose up -d
```

## Documentation

- Setup guide: [`docs/SETUP.md`](docs/SETUP.md)
- Full specification: [`docs/`](docs/)
