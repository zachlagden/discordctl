import json
from types import SimpleNamespace

import pytest
from aiohttp.test_utils import TestClient, TestServer

from claude_control.daemon.server import build_app, compute_gating
from claude_control.ops.registry import Registry


def test_compute_gating_read_op():
    payload = SimpleNamespace(dry_run=True, confirm=False)
    assert compute_gating(False, True, payload) == (False, False)


def test_compute_gating_mutation_needs_confirm():
    payload = SimpleNamespace(dry_run=True, confirm=False)
    assert compute_gating(True, True, payload) == (True, True)


def test_compute_gating_confirmed():
    payload = SimpleNamespace(dry_run=False, confirm=True)
    assert compute_gating(True, True, payload) == (False, False)


def test_compute_gating_write_disabled_forces_dry_run():
    payload = SimpleNamespace(dry_run=False, confirm=True)
    assert compute_gating(True, False, payload) == (True, False)


class FakeAudit:
    def __init__(self):
        self.records = []

    async def record(self, **fields):
        self.records.append(fields)


async def _client(registry, write_enabled=True):
    from claude_control.config import Config

    cfg = Config(
        discord_token="t", bus_host="127.0.0.1", bus_port=0, bus_token="secret",
        write_enabled=write_enabled, allowed_guild_ids=frozenset({1}),
        default_guild_id=1, log_level="INFO", sentry_dsn=None, audit_path="x",
    )
    app = build_app(bot=SimpleNamespace(), config=cfg, audit=FakeAudit())
    app["registry"] = registry
    return TestClient(TestServer(app))


async def test_unauthorized_without_token():
    client = await _client(Registry())
    await client.start_server()
    resp = await client.post("/v1/op", json={"op": "x"})
    assert resp.status == 401
    await client.close()


async def test_read_op_executes(monkeypatch):
    reg = Registry()

    async def info(ctx, args):
        return {"hello": "world"}

    reg.register("guild.info", info)
    client = await _client(reg)
    await client.start_server()
    resp = await client.post(
        "/v1/op", json={"op": "guild.info"},
        headers={"Authorization": "Bearer secret"},
    )
    body = await resp.json()
    assert resp.status == 200
    assert body["ok"] is True
    assert body["data"] == {"hello": "world"}
    await client.close()


async def test_mutation_without_confirm_is_dry_run():
    reg = Registry()
    called = {"live": False}

    async def ban(ctx, args):
        if not ctx.dry_run:
            called["live"] = True
        return {"planned": ctx.dry_run}

    reg.register("member.ban", ban, mutating=True)
    client = await _client(reg)
    await client.start_server()
    resp = await client.post(
        "/v1/op", json={"op": "member.ban", "args": {}},
        headers={"Authorization": "Bearer secret"},
    )
    body = await resp.json()
    assert body["dry_run"] is True
    assert body["must_confirm"] is True
    assert called["live"] is False
    await client.close()
