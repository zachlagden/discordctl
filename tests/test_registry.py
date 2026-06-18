import pytest

from discordctl.ops.registry import (
    REGISTRY,
    HandlerError,
    Registry,
    op,
    plan,
)


def test_register_and_get():
    reg = Registry()

    async def handler(ctx, args):
        return {"ok": 1}

    reg.register("x.test", handler, mutating=True)
    assert reg.get("x.test") is handler
    assert reg.is_mutating("x.test") is True
    assert "x.test" in reg.ops()


def test_duplicate_registration_raises():
    reg = Registry()

    async def handler(ctx, args):
        return None

    reg.register("dup", handler)
    with pytest.raises(RuntimeError):
        reg.register("dup", handler)


def test_op_decorator_registers_globally():
    @op("decorated.read")
    async def _h(ctx, args):
        return 1

    assert REGISTRY.get("decorated.read") is not None
    assert REGISTRY.is_mutating("decorated.read") is False


def test_plan_shape():
    assert plan("ban", user_id=5) == {"planned": True, "action": "ban", "user_id": 5}


def test_handler_error_code():
    err = HandlerError("nope", code="not_found")
    assert err.code == "not_found"
    assert str(err) == "nope"
