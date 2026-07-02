# WHAT THIS FILE IS
# A small wrapper around Supabase (our login/auth provider). It builds a "service
# role" client — an admin connection with full access — used on the SERVER only to
# verify a user's login token. WHY server-only: the service-role key can do anything,
# so it must NEVER be sent to the browser.

from functools import lru_cache
from typing import Optional

from supabase import Client, create_client
from supabase_auth.types import User

from app.config import get_settings


# Build the admin client once and reuse it (@lru_cache = build-once-then-reuse).
@lru_cache
def admin() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_user_from_token(token: str) -> Optional[User]:
    # Ask Supabase "who does this login token belong to?" It checks the token against
    # Supabase's auth server and returns that user.
    # CONTRACT (verified against supabase_auth 2.31.0): get_user RAISES AuthApiError
    # for an INVALID/expired token; it returns a response with `user=None` only for an
    # empty token string. So callers must handle the raised error — they cannot rely on
    # a None return to mean "bad token". (deps.require_user catches the raise and turns
    # it into a 401.) Kept as its own function so tests can stand in a fake with no network.
    response = admin().auth.get_user(token)
    return response.user if response else None
