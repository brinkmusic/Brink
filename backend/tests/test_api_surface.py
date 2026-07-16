# WHAT THIS FILE IS
# A route-inventory test for the public /api/* surface. WHY: T61 is the QA gate,
# so we want one cheap test that fails when someone adds or removes an API endpoint
# without updating tests/docs. The behavior of each endpoint still lives in the
# route-specific test files (test_posts.py, test_artist.py, etc.).

from app.main import app


EXPECTED_API_ROUTES = {
    ("GET", "/api/health"),
    ("POST", "/api/posts"),
    ("GET", "/api/posts"),
    ("POST", "/api/posts/{post_id}/reactions"),
    ("DELETE", "/api/posts/{post_id}/reactions"),
    ("POST", "/api/posts/{post_id}/comments"),
    ("GET", "/api/posts/{post_id}/comments"),
    ("POST", "/api/follow/{user_id}"),
    ("DELETE", "/api/follow/{user_id}"),
    ("GET", "/api/feed"),
    ("GET", "/api/me/now-playing"),
    ("POST", "/api/snapshot"),
    ("POST", "/api/artist/sign-upload"),
    ("POST", "/api/artist/posts"),
    ("POST", "/api/artist/posts/{post_id}/reactions"),
    ("DELETE", "/api/artist/posts/{post_id}/reactions"),
    ("POST", "/api/artist/posts/{post_id}/comments"),
    ("GET", "/api/artist/posts/{post_id}/comments"),
    ("GET", "/api/artist/posts/{post_id}/engagement"),
    ("GET", "/api/search"),
    ("GET", "/api/users/search"),
    ("GET", "/api/users/{user_id}/followers"),
    ("GET", "/api/users/{user_id}/following"),
}


def test_api_route_surface_matches_tested_inventory():
    actual = set()
    for path, operations in app.openapi()["paths"].items():
        if not path.startswith("/api/"):
            continue
        for method in operations:
            normalized = method.upper()
            if normalized in {"HEAD", "OPTIONS"}:
                continue
            actual.add((normalized, path))

    assert actual == EXPECTED_API_ROUTES
