import pytest
from pydantic import ValidationError

from claude_control.schemas import OpRequest


def test_defaults():
    req = OpRequest(op="guild.info")
    assert req.args == {}
    assert req.dry_run is True
    assert req.confirm is False
    assert req.yes_really is False


def test_forbids_extra_keys():
    with pytest.raises(ValidationError):
        OpRequest(op="x", bogus=1)
