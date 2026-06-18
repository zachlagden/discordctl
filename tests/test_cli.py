from claude_control.cli.dctl import build_body, parse_arg


def test_parse_arg_int():
    assert parse_arg("limit=5") == ("limit", 5)


def test_parse_arg_bool():
    assert parse_arg("nsfw=true") == ("nsfw", True)


def test_parse_arg_json_list():
    assert parse_arg("role_ids=[1,2]") == ("role_ids", [1, 2])


def test_parse_arg_string():
    assert parse_arg("name=general") == ("name", "general")


def test_build_body_confirm_sets_live():
    body = build_body("member.ban", ["user_id=5"], confirm=True, yes_really=False)
    assert body == {
        "op": "member.ban", "args": {"user_id": 5},
        "confirm": True, "dry_run": False, "yes_really": False,
    }


def test_build_body_default_dry_run():
    body = build_body("member.ban", ["user_id=5"], confirm=False, yes_really=False)
    assert body["dry_run"] is True
    assert body["confirm"] is False
