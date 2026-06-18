from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

log = logging.getLogger(__name__)

Handler = Callable[["BusContext", dict[str, Any]], Awaitable[Any]]


class HandlerError(Exception):
    def __init__(self, message: str, *, code: str = "error") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class BusContext:
    bot: Any
    dry_run: bool
    confirm: bool
    yes_really: bool
    actor: str
    write_enabled: bool
    allowed_guild_ids: frozenset[int]
    default_guild_id: int | None


class Registry:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}
        self._mutating: set[str] = set()

    def register(self, name: str, handler: Handler, *, mutating: bool = False) -> None:
        if name in self._handlers:
            raise RuntimeError(f"op {name!r} already registered")
        self._handlers[name] = handler
        if mutating:
            self._mutating.add(name)

    def get(self, name: str) -> Handler | None:
        return self._handlers.get(name)

    def is_mutating(self, name: str) -> bool:
        return name in self._mutating

    def ops(self) -> list[str]:
        return sorted(self._handlers)

    def mutating_ops(self) -> set[str]:
        return set(self._mutating)


REGISTRY = Registry()


def op(name: str, *, mutating: bool = False) -> Callable[[Handler], Handler]:
    def decorator(fn: Handler) -> Handler:
        REGISTRY.register(name, fn, mutating=mutating)
        return fn

    return decorator


def plan(action: str, **details: Any) -> dict[str, Any]:
    return {"planned": True, "action": action, **details}


def load_all_handlers() -> None:
    from claude_control.ops import handlers as handlers_pkg

    for mod in pkgutil.iter_modules(handlers_pkg.__path__):
        importlib.import_module(f"claude_control.ops.handlers.{mod.name}")
