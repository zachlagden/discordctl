from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any


def mk_request_id() -> str:
    return "req_" + uuid.uuid4().hex


def now_ms() -> int:
    return int(time.time() * 1000)


class AuditWriter:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()

    async def record(self, **fields: Any) -> None:
        fields.setdefault("ts", now_ms())
        line = json.dumps(fields, default=str) + "\n"
        async with self._lock:
            await asyncio.to_thread(self._append, line)

    def _append(self, line: str) -> None:
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line)
