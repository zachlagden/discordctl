from __future__ import annotations

import sys
import urllib.parse


def build_invite_url(client_id: str, permissions: int = 8) -> str:
    query = urllib.parse.urlencode({
        "client_id": client_id,
        "permissions": permissions,
        "scope": "bot applications.commands",
    })
    return f"https://discord.com/api/oauth2/authorize?{query}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: uv run python scripts/invite_url.py <CLIENT_ID> [PERMISSIONS]")
    perms = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    print(build_invite_url(sys.argv[1], perms))
