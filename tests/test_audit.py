import json

from claude_control.ops.audit import AuditWriter, mk_request_id, now_ms


def test_mk_request_id_unique():
    assert mk_request_id() != mk_request_id()


def test_now_ms_is_int():
    assert isinstance(now_ms(), int)


async def test_record_appends_jsonl(tmp_path):
    path = tmp_path / "audit.jsonl"
    writer = AuditWriter(str(path))
    await writer.record(op="member.ban", ok=True, request_id="req_1")
    await writer.record(op="member.kick", ok=False, request_id="req_2")
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["op"] == "member.ban"
    assert first["ok"] is True
    assert "ts" in first


async def test_record_creates_missing_parent_dir(tmp_path):
    path = tmp_path / "nested" / "deeper" / "audit.jsonl"
    writer = AuditWriter(str(path))
    await writer.record(op="x", ok=True)
    assert path.exists()
    assert path.read_text().strip()
