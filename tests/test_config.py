import pytest

from claude_control.config import Config


def test_from_env_parses_all(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "tok")
    monkeypatch.setenv("BUS_TOKEN", "bus")
    monkeypatch.setenv("ALLOWED_GUILD_IDS", "111, 222")
    monkeypatch.setenv("DEFAULT_GUILD_ID", "111")
    monkeypatch.setenv("WRITE_ENABLED", "false")
    cfg = Config.from_env()
    assert cfg.discord_token == "tok"
    assert cfg.bus_token == "bus"
    assert cfg.allowed_guild_ids == frozenset({111, 222})
    assert cfg.default_guild_id == 111
    assert cfg.write_enabled is False
    assert cfg.bus_port == 8765


def test_from_env_requires_discord_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    monkeypatch.setenv("BUS_TOKEN", "bus")
    with pytest.raises(RuntimeError):
        Config.from_env()


def test_from_env_requires_bus_token(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "tok")
    monkeypatch.delenv("BUS_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        Config.from_env()
