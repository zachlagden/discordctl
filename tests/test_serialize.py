from tests.conftest import make_channel, make_member, make_role

from discordctl.ops.serialize import channel_dict, member_dict, role_dict


def test_role_dict_stringifies_id():
    d = role_dict(make_role(id=10, name="mod"))
    assert d["id"] == "10"
    assert d["name"] == "mod"
    assert d["color"] == "#5865f2"
    assert d["permissions"] == "8"


def test_member_dict_lists_role_ids():
    member = make_member(id=100, roles=[make_role(id=10), make_role(id=11)])
    d = member_dict(member)
    assert d["id"] == "100"
    assert d["role_ids"] == ["10", "11"]


def test_channel_dict_type_name():
    d = channel_dict(make_channel(id=200, type_name="text"))
    assert d["id"] == "200"
    assert d["type"] == "text"
