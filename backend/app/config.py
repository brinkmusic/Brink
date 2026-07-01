# WHAT THIS FILE IS
# Loads the app's settings (like the database address) from a hidden ".env" file
# and from the server's environment. WHY: secrets like the database URL must never
# be written into the code. We keep them in a .env file (which git ignores) and
# read them here, in one place, so the rest of the app just asks for "settings".

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


# Returns the settings. @lru_cache means "build this once, then reuse it" — we don't
# re-read the .env file every time something needs a setting.
@lru_cache
def get_settings() -> Settings:
    return Settings()
