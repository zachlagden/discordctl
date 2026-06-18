from __future__ import annotations

import hmac
import logging
from typing import Any

from aiohttp import web
from pydantic import ValidationError

from claude_control.config import Config
from claude_control.ops.audit import AuditWriter, mk_request_id, now_ms
from claude_control.ops.registry import REGISTRY, BusContext, HandlerError
from claude_control.schemas import OpRequest

log = logging.getLogger(__name__)


def compute_gating(mutating: bool, write_enabled: bool, payload: Any) -> tuple[bool, bool]:
    if not mutating:
        return False, False
    if not write_enabled:
        return True, False
    if not payload.confirm:
        return True, True
    return False, False


def build_app(bot: Any, config: Config, audit: AuditWriter) -> web.Application:
    app = web.Application(middlewares=[_make_auth(config)])
    app["bot"] = bot
    app["config"] = config
    app["audit"] = audit
    app["registry"] = REGISTRY
    app.router.add_get("/v1/health", _health)
    app.router.add_get("/v1/ops", _list_ops)
    app.router.add_post("/v1/op", _handle_op)
    return app


def _make_auth(config: Config):
    @web.middleware
    async def auth(request: web.Request, handler):
        if (request.remote or "") not in ("127.0.0.1", "::1"):
            return web.json_response({"ok": False, "error": "forbidden"}, status=403)
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
        provided = header[len("Bearer "):].strip()
        if not hmac.compare_digest(provided, config.bus_token):
            return web.json_response({"ok": False, "error": "unauthorized"}, status=401)
        return await handler(request)

    return auth


async def _health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "data": {"status": "ready"}})


async def _list_ops(request: web.Request) -> web.Response:
    registry = request.app["registry"]
    ops = [{"name": n, "mutating": registry.is_mutating(n)} for n in registry.ops()]
    return web.json_response({"ok": True, "data": {"ops": ops}})


async def _handle_op(request: web.Request) -> web.Response:
    registry = request.app["registry"]
    config: Config = request.app["config"]
    audit: AuditWriter = request.app["audit"]
    request_id = mk_request_id()
    started = now_ms()

    try:
        raw = await request.json()
    except Exception as exc:
        return web.json_response(
            {"ok": False, "error": f"bad json: {exc}", "request_id": request_id}, status=400
        )

    try:
        payload = OpRequest.model_validate(raw)
    except ValidationError as exc:
        return web.json_response(
            {"ok": False, "error": exc.errors(), "request_id": request_id}, status=400
        )

    handler = registry.get(payload.op)
    if handler is None:
        return web.json_response(
            {"ok": False, "error": f"unknown op {payload.op!r}", "request_id": request_id},
            status=404,
        )

    mutating = registry.is_mutating(payload.op)
    effective_dry_run, must_confirm = compute_gating(mutating, config.write_enabled, payload)

    ctx = BusContext(
        bot=request.app["bot"], dry_run=effective_dry_run, confirm=payload.confirm,
        yes_really=payload.yes_really, actor="claude-code",
        write_enabled=config.write_enabled, allowed_guild_ids=config.allowed_guild_ids,
        default_guild_id=config.default_guild_id,
    )

    ok, error, data, status = True, None, None, 200
    try:
        data = await handler(ctx, payload.args)
    except HandlerError as exc:
        ok, error, status = False, {"message": str(exc), "code": exc.code}, 400
    except Exception as exc:
        log.exception("unhandled error in op %s", payload.op)
        ok, error, status = False, f"internal: {type(exc).__name__}: {exc}", 500

    body = {
        "ok": ok, "data": data, "error": error, "request_id": request_id,
        "dry_run": effective_dry_run if mutating else None,
    }
    if must_confirm:
        body["must_confirm"] = True

    await audit.record(
        request_id=request_id, op=payload.op, args=payload.args, actor=ctx.actor,
        dry_run=effective_dry_run if mutating else False, confirm=payload.confirm,
        ok=ok, duration_ms=now_ms() - started, error=error, result=data,
    )
    return web.json_response(body, status=status)
