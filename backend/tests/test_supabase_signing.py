# WHAT THIS FILE IS
# Checks the resilient artist-image signing helper (app/security/supabase.py):
#   create_signed_read_url_or_blank(bucket, path) -> a signed read URL, or "" if signing FAILS.
# WHY it exists (T103): a private-bucket signing failure (bad creds, missing object, Storage outage)
# must NEVER take down the feed or the artist page — a blank URL lets the template show a placeholder
# instead. These tests stub the underlying create_signed_read_url so no real Supabase is touched.

from app.security import supabase


# On success the wrapper just passes the signed URL straight through (no behavior change).
def test_or_blank_passes_through_on_success(monkeypatch):
    monkeypatch.setattr(
        supabase, "create_signed_read_url",
        lambda bucket, path, expires_in=3600: f"https://signed/{bucket}/{path}",
    )
    assert supabase.create_signed_read_url_or_blank("artist-images", "a/b.png") == \
        "https://signed/artist-images/a/b.png"


# When the underlying signer RAISES (the production incident: StorageApiError 404), the wrapper
# swallows it and returns "" — the caller renders a placeholder instead of 500ing / blanking a page.
def test_or_blank_returns_empty_on_failure(monkeypatch):
    def boom(bucket, path, expires_in=3600):
        raise RuntimeError("StorageApiError: Object not found")

    monkeypatch.setattr(supabase, "create_signed_read_url", boom)
    assert supabase.create_signed_read_url_or_blank("artist-images", "a/b.png") == ""
