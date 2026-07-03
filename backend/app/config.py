# WHAT THIS FILE IS
# Loads the app's settings (like the database address) from a hidden ".env" file
# and from the server's environment. WHY: secrets like the database URL must never
# be written into the code. We keep them in a .env file (which git ignores) and
# read them here, in one place, so the rest of the app just asks for "settings".

import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Work out where the .env file is. It lives at the project root, and this file is
# two folders deep (backend/app/config.py), so we go up two levels to find it.
_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


# The list of settings the app expects. Each name here is matched (case-insensitively)
# to a line in the .env file, e.g. database_url <- DATABASE_URL=...
class Settings(BaseSettings):
    # Read from _ROOT_ENV, and ignore any other variables in that file we don't list.
    model_config = SettingsConfigDict(env_file=_ROOT_ENV, extra="ignore")

    database_url: str            # required: how the app connects to the database
    direct_url: Optional[str] = None  # optional: a direct connection used for migrations

    # Auth + crypto settings (added in T06). All required in a real run; they live in
    # the same root .env. supabase_* let the server verify logins and act as admin;
    # token_enc_key encrypts the Spotify tokens we store.
    supabase_url: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    token_enc_key: Optional[str] = None


# Returns the settings. @lru_cache means "build this once, then reuse it" — we don't
# re-read the .env file every time something needs a setting.
@lru_cache
def get_settings() -> Settings:
    return Settings()


# The secrets a real deployment cannot run without. database_url is already enforced by
# pydantic (it has no default); these three are Optional on the model (so tests and
# migrations can import the app without them) but MUST be present when actually serving.
_REQUIRED_IN_PRODUCTION = ("supabase_url", "supabase_service_role_key", "token_enc_key")


def _is_test_environment() -> bool:
    # The escape hatch: during automated tests the app is imported with no real .env
    # (CI has no secrets) and each test fakes the settings it needs. So we skip the
    # production fail-fast whenever pytest is the process running us.
    return "pytest" in sys.modules


def verify_required_settings() -> None:
    # Fail fast at startup when a required secret is missing, so a misdeployed server
    # crashes loudly on boot instead of booting "healthy" and then returning 500s on
    # every request (the /api/health check only tests the database, so it would not
    # catch a missing SUPABASE_* / TOKEN_ENC_KEY). Called from main.py's startup.
    if _is_test_environment():
        return
    settings = get_settings()
    missing = [name for name in _REQUIRED_IN_PRODUCTION if not getattr(settings, name)]
    if missing:
        raise RuntimeError(
            "Missing required environment settings: "
            + ", ".join(name.upper() for name in missing)
        )
