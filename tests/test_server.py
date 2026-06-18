from types import SimpleNamespace

import discord
import pytest
from aiohttp.test_utils import TestClient, TestServer

from claude_control.daemon.server import build_app, compute_gating, KEY_REGISTRY
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
    app[KEY_REGISTRY] = registry
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


async def test_health_requires_auth():
    client = await _client(Registry())
    await client.start_server()
    resp = await client.get("/v1/health")
    assert resp.status == 401
    await client.close()


async def test_ops_requires_auth():
    client = await _client(Registry())
    await client.start_server()
    resp = await client.get("/v1/ops")
    assert resp.status == 401
    await client.close()


def _resp(status, headers=None):
    return SimpleNamespace(status=status, reason="x", headers=headers or {})


async def test_forbidden_maps_403():
    reg = Registry()
    async def h(ctx, args):
        raise discord.Forbidden(_resp(403), "Missing Permissions")
    reg.register("x.forbidden", h)
    client = await _client(reg)
    await client.start_server()
    resp = await client.post("/v1/op", json={"op": "x.forbidden"},
                             headers={"Authorization": "Bearer secret"})
    assert resp.status == 403
    body = await resp.json()
    assert body["error"]["code"] == "forbidden"
    await client.close()


async def test_notfound_maps_404():
    reg = Registry()
    async def h(ctx, args):
        raise discord.NotFound(_resp(404), "Unknown")
    reg.register("x.missing", h)
    client = await _client(reg)
    await client.start_server()
    resp = await client.post("/v1/op", json={"op": "x.missing"},
                             headers={"Authorization": "Bearer secret"})
    assert resp.status == 404
    await client.close()


async def test_httpexception_maps_status_and_retry_after():
    reg = Registry()
    async def h(ctx, args):
        raise discord.HTTPException(_resp(429, {"Retry-After": "5"}), "rate limited")
    reg.register("x.ratelimited", h)
    client = await _client(reg)
    await client.start_server()
    resp = await client.post("/v1/op", json={"op": "x.ratelimited"},
                             headers={"Authorization": "Bearer secret"})
    assert resp.status == 429
    body = await resp.json()
    assert body["error"]["retry_after"] == 5.0
    await client.close()
