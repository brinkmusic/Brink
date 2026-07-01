# WHAT THIS FILE IS
# A small wrapper around Supabase (our login/auth provider). It builds a "service
# role" client — an admin connection with full access — used on the SERVER only to
# verify a user's login token. WHY server-only: the service-role key can do anything,
# so it must NEVER be sent to the browser.

from functools import lru_cache
from typing import Any, Optional

from supabase import Client, create_client

from app.config import get_settings


# Build the admin client once and reuse it (@lru_cache = build-once-then-reuse).
@lru_cache
def admin() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_user_from_token(token: str) -> Optional[Any]:
    # Ask Supabase "who does this login token belong to?" It checks the token against
    # Supabase's auth server and returns that user (or None if the token is invalid).
    # Kept as its own function so tests can easily stand in a fake without a network call.
    response = admin().auth.get_user(token)
    return response.user if response else None
