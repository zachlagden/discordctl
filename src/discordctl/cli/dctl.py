from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def parse_arg(raw: str) -> tuple[str, Any]:
    if "=" not in raw:
        raise SystemExit(f"arg must be key=value, got {raw!r}")
    key, value = raw.split("=", 1)
    if value.startswith("@"):
        path = Path(value[1:]).expanduser()
        if not path.exists():
            raise SystemExit(f"file not found: {path}")
        text = path.read_text(encoding="utf-8")
        try:
            return key, json.loads(text)
        except json.JSONDecodeError:
            return key, text
    if value[:1] in ("[", "{"):
        try:
            return key, json.loads(value)
        except json.JSONDecodeError:
            return key, value
    if value in ("true", "false"):
        return key, value == "true"
    if value.lstrip("-").isdigit():
        return key, int(value)
    return key, value


def build_body(op: str, arg_list: list[str], *, confirm: bool, yes_really: bool) -> dict[str, Any]:
    args: dict[str, Any] = {}
    for raw in arg_list:
        key, value = parse_arg(raw)
        args[key] = value
    body: dict[str, Any] = {"op": op, "args": args, "confirm": confirm, "yes_really": yes_really}
    body["dry_run"] = not confirm
    return body


def _base_url() -> str:
    explicit = os.getenv("BUS_URL")
    if explicit:
        return explicit.rstrip("/")
    host = os.getenv("BUS_HOST", "127.0.0.1")
    port = os.getenv("BUS_PORT", "8765")
    return f"http://{host}:{port}"


def _headers() -> dict[str, str]:
    token = os.getenv("BUS_TOKEN")
    if not token:
        raise SystemExit("BUS_TOKEN not set in env/.env")
    return {"Authorization": f"Bearer {token.strip()}", "Content-Type": "application/json"}


def _request(method: str, path: str, body: dict | None) -> tuple[int, str]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(_base_url() + path, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()
    except urllib.error.URLError as exc:
        print(f"connection error: {exc}", file=sys.stderr)
        raise SystemExit(3)


def _emit(text: str, *, as_json: bool) -> None:
    if as_json:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
        return
    try:
        print(json.dumps(json.loads(text), indent=2, default=str))
    except json.JSONDecodeError:
        print(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dctl", description="discordctl CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    sub.add_parser("ops")
    desc = sub.add_parser("describe")
    desc.add_argument("op")
    op_cmd = sub.add_parser("op")
    op_cmd.add_argument("name")
    op_cmd.add_argument("--arg", action="append", default=[])
    op_cmd.add_argument("--confirm", action="store_true")
    op_cmd.add_argument("--yes-really", dest="yes_really", action="store_true")
    op_cmd.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "health":
        status, text = _request("GET", "/v1/health", None)
        _emit(text, as_json=False)
        return 0 if status == 200 else 1
    if args.cmd == "ops":
        status, text = _request("GET", "/v1/ops", None)
        _emit(text, as_json=False)
        return 0 if status == 200 else 1
    if args.cmd == "describe":
        status, text = _request("GET", "/v1/ops", None)
        payload = json.loads(text)
        match = [o for o in payload.get("data", {}).get("ops", []) if o["name"] == args.op]
        print(json.dumps(match[0] if match else {"error": "unknown op"}, indent=2))
        return 0 if match else 1

    body = build_body(args.name, args.arg, confirm=args.confirm, yes_really=args.yes_really)
    status, text = _request("POST", "/v1/op", body)
    _emit(text, as_json=args.json)
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
