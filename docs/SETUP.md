# Setup Guide

This guide takes the DigiGrow bot from "exists in the Developer Portal" to "running and reachable
from `dctl`". Follow the steps in order.

## Prerequisites

- `uv` installed (the project uses `uv` for everything — never `pip`).
- Access to the Discord application in the Developer Portal.
- Manage Server permission on the DigiGrow guild (to authorize the invite).

```bash
uv sync
```

## 1. Developer Portal

Open the existing application at <https://discord.com/developers/applications> → select it → **Bot** tab.

### Privileged intents (required)

The daemon builds its gateway connection with `discord.Intents.all()` (see
`src/discordctl/daemon/bot.py`). That requires **all three** privileged intents to be toggled
**ON** under **Bot → Privileged Gateway Intents**:

- **Presence Intent**
- **Server Members Intent**
- **Message Content Intent**

If **any** of the three is off, Discord rejects the gateway connection at login — the daemon dies
immediately with close code **4014** (`PrivilegedIntentsRequired`) and never reaches the
`control bus on ...` log line. The DigiGrow bot already has all three enabled; verify before
continuing.

Copy the bot token from this tab. It goes into `.env` as `DISCORD_TOKEN` in the next step.
For the DigiGrow bot the token is **already in `.env`**, so you can skip this — do **not** click
"Reset Token" (that invalidates the current token and would break the running daemon). Only reset
if no token exists anywhere.

## 2. `.env`

```bash
cp .env.example .env
```

For the DigiGrow bot, `DISCORD_TOKEN` and `BUS_TOKEN` are **already set** in `.env` — do not
regenerate or overwrite them. You only need to fill in the guild fields. If you are setting up a
fresh copy from `.env.example`, then also:

- Paste the bot token into `DISCORD_TOKEN`.
- Generate a high-entropy bus token:

  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

  and put it in `BUS_TOKEN`. It must stay a 256-bit (64 hex char) random value — the control bus
  authenticates every request against it with a constant-time compare.

### Guild allowlist (do not skip)

Set both guild fields to the DigiGrow guild ID:

```dotenv
ALLOWED_GUILD_IDS=<digigrow_guild_id>
DEFAULT_GUILD_ID=<digigrow_guild_id>
```

`ALLOWED_GUILD_IDS` is a comma-separated allowlist. **Leaving it empty DISABLES the allowlist** —
every guild the bot is a member of becomes reachable through the bus. This bot is invited with
**Administrator**, so an empty allowlist means any guild it lands in is fully controllable. Always
set `ALLOWED_GUILD_IDS` once the guild ID is known; treat an empty value as a misconfiguration, not
a default.

To get the guild ID: Discord → **User Settings → Advanced → Developer Mode** (toggle on), then
**right-click the server icon → Copy Server ID**.

### Networking and security

- The control bus binds **`127.0.0.1` only** and rejects any peer that is not loopback
  (`127.0.0.1` / `::1`) before checking the token. `docker-compose.yml` uses
  `network_mode: host` specifically so the host-run `dctl` can reach that loopback bus.
- **`BUS_HOST` must remain a loopback address (`127.0.0.1`).** Never set it to `0.0.0.0` — that
  would expose an Administrator-permission control plane on every interface.
- Keep `BUS_TOKEN` high-entropy (256-bit hex). Never commit `.env`; it is gitignored.

## 3. Invite the bot

Generate the OAuth2 authorize URL (the `<CLIENT_ID>` is the **Application ID** from the portal's
**General Information** tab):

```bash
uv run python scripts/invite_url.py <CLIENT_ID>
```

Open the printed URL, pick the **DigiGrow** server from the dropdown, and authorize. The URL
requests `scope=bot applications.commands` with **Administrator** permissions (`permissions=8`).

## 4. Run the daemon

```bash
uv run python -m discordctl
# or:
docker compose up -d
```

On a healthy start you will see, in the logs:

```
control bus on 127.0.0.1:8765 as <bot name>
```

That line means the gateway is connected and the bus is listening. If you don't see it, check the
privileged intents (step 1) and the token (step 2).

## 5. Verify

From a shell on the same host (this is also how Claude / the Bash tool drive it):

```bash
uv run dctl health
uv run dctl ops
uv run dctl op guild.info
```

- `health` should return `{"ok": true, "data": {"status": "ready"}}`.
- `ops` lists every registered operation and whether it mutates.
- `op guild.info` is a read; it resolves the default guild and returns its info. This requires
  `DEFAULT_GUILD_ID` to be set (step 2) — otherwise it errors with `guild_id required (no default
  configured)`; you can instead target a guild explicitly with `--arg guild_id=<id>`.

### First mutation: dry-run → confirm

Mutating ops are **dry-run by default**. Run once without `--confirm` to preview the plan, then
re-run with `--confirm` to apply it:

```bash
# Preview (dry run) — returns a plan, changes nothing:
uv run dctl op guild.edit --arg name="DigiGrow"

# Apply — same command plus --confirm:
uv run dctl op guild.edit --arg name="DigiGrow" --confirm
```

The dry run echoes the intended change so you can confirm it is correct before committing. Every
op (dry-run and applied) is appended to the audit log at `AUDIT_PATH` (`./audit.jsonl`).
