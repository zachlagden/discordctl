# Live smoke test (run once after the bot is invited)

A manual, end-to-end check against a **real** DigiGrow guild. It is intentionally not
automated — it mutates a live server. Run it once after completing `docs/SETUP.md`
(bot invited, `.env` filled, `ALLOWED_GUILD_IDS`/`DEFAULT_GUILD_ID` set). It creates and
then deletes a throwaway `zz-smoke` role, so it leaves no residue.

All commands run from the repo root on the same host as the daemon.

## 1. Start the daemon

```bash
uv run python -m claude_control
```

- [ ] Log shows `control bus on 127.0.0.1:8765 as <bot>`.
- [ ] The bot appears **online** in the DigiGrow member list.

Leave it running; open a second shell for the `dctl` calls below.

## 2. Liveness + read ops

```bash
uv run dctl health
uv run dctl ops
uv run dctl op guild.info
uv run dctl op role.list
uv run dctl op channel.list
```

- [ ] `health` → `{"ok": true, "data": {"status": "ready"}}`.
- [ ] `ops` lists 75 operations.
- [ ] `guild.info` returns the DigiGrow guild name + counts.
- [ ] `role.list` / `channel.list` return JSON arrays.

## 3. Dry-run gate (no mutation without `--confirm`)

```bash
uv run dctl op role.create --arg name=zz-smoke
```

- [ ] Response has `"dry_run": true` and `"must_confirm": true`.
- [ ] No `zz-smoke` role appears in Discord.

## 4. Confirmed mutation + cleanup

```bash
uv run dctl op role.create --arg name=zz-smoke --confirm
```

- [ ] Response `"ok": true` with the new role's id; `zz-smoke` now exists in Discord.

```bash
uv run dctl op role.delete --arg role_name=zz-smoke --confirm
```

- [ ] `zz-smoke` is gone from Discord.

## 5. Guild allowlist guard

Pick any guild ID that is **not** in `ALLOWED_GUILD_IDS`:

```bash
uv run dctl op guild.info --arg guild_id=000000000000000000
```

- [ ] Response `"ok": false` with `error.code == "forbidden"`.

## 6. Owner-refusal guard

Use the DigiGrow guild owner's user ID:

```bash
uv run dctl op member.ban --arg user_id=<owner_id> --confirm
```

- [ ] Response `"ok": false` with `error.code == "refused"` — the owner is never banned.

## 7. Destructive-purge guard

In a low-stakes test channel (this is destructive above the threshold — use a scratch channel):

```bash
uv run dctl op message.purge --arg channel_id=<channel_id> --arg limit=500
```

- [ ] Response `"ok": false` with `error.code == "needs_yes_really"` (purge > 100 is gated).
- [ ] Re-running with `--yes-really --confirm` proceeds (only if you actually intend to delete).

## 8. Global kill switch

Stop the daemon, set `WRITE_ENABLED=false` in `.env`, restart it, then:

```bash
uv run dctl op role.create --arg name=zz-killswitch --confirm
```

- [ ] Response still has `"dry_run": true` despite `--confirm` — no role created.
- [ ] Restore `WRITE_ENABLED=true` and restart when done.

## 9. Audit log

```bash
tail -n 20 audit.jsonl
```

- [ ] One JSON line per call above, each with `op`, `ok`, `dry_run`, `duration_ms`, and
      `actor: "claude-code"`.
- [ ] The dry-run calls show `dry_run: true`; the confirmed ones `dry_run: false`.

---

Once every box is checked, the control plane is verified end-to-end against the live guild.
