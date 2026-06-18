from scripts.invite_url import build_invite_url


def test_invite_url_admin():
    url = build_invite_url("123456789")
    assert "client_id=123456789" in url
    assert "permissions=8" in url
    assert "scope=bot" in url
    assert "applications.commands" in url
