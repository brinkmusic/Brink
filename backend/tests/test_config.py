# WHAT THIS FILE IS
# Checks the startup fail-fast (app/config.verify_required_settings). WHY: a server
# deployed without its secrets must crash loudly on boot, not quietly serve 500s on
# every request (the health check only tests the database, so a missing SUPABASE_* or
# TOKEN_ENC_KEY would otherwise let a broken deploy look healthy).

from types import SimpleNamespace

import pytest

from app import config


def _settings(**overrides):
    # A stand-in Settings object with every required value present by default; pass
    # overrides to blank one out and exercise the failure path.
    base = dict(
        database_url="postgresql://x",
        direct_url=None,
        supabase_url="u",
        supabase_service_role_key="k",
        token_enc_key="t",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# Outside tests, a missing required secret makes startup raise a clear, named error.
def test_missing_required_setting_raises(monkeypatch):
    monkeypatch.setattr(config, "_is_test_environment", lambda: False)
    monkeypatch.setattr(config, "get_settings", lambda: _settings(token_enc_key=None))
    with pytest.raises(RuntimeError, match="TOKEN_ENC_KEY"):
        config.verify_required_settings()


# When all required secrets are present, startup verification passes silently.
def test_all_settings_present_ok(monkeypatch):
    monkeypatch.setattr(config, "_is_test_environment", lambda: False)
    monkeypatch.setattr(config, "get_settings", lambda: _settings())
    config.verify_required_settings()  # no raise


# The test-environment escape hatch skips the check entirely, so CI (which has no real
# .env) can import and run the app without secrets even when nothing is configured.
def test_test_environment_skips_check(monkeypatch):
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: _settings(supabase_url=None, supabase_service_role_key=None, token_enc_key=None),
    )
    config.verify_required_settings()  # skipped because pytest is running -> no raise
