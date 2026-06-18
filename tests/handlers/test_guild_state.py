from claude_control.ops.handlers.guild_state import diff_snapshots


def test_diff_detects_create_and_delete():
    current = {"roles": [{"name": "mod"}], "categories": [], "channels": []}
    desired = {"roles": [{"name": "admin"}], "categories": [], "channels": []}
    result = diff_snapshots(current, desired)
    assert result["roles"]["create"] == [{"name": "admin"}]
    assert result["roles"]["delete"] == [{"name": "mod"}]


def test_diff_detects_no_change():
    snap = {"roles": [{"name": "mod"}], "categories": [], "channels": []}
    result = diff_snapshots(snap, snap)
    assert result["roles"]["create"] == []
    assert result["roles"]["delete"] == []
