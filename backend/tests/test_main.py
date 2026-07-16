# WHAT THIS FILE IS
# Tests that every error response — validation failures, unknown paths, and server
# errors — comes back in the standard { "error": "..." } envelope, not in FastAPI's
# default { "detail": ... } shape. WHY: the frontend has one rule for reading results
# and will break silently if some errors bypass the envelope (ADR-0010, ADR-0007 §1).

# The `client` fixture (a fake HTTP client) comes from conftest.py.


# When a request body is malformed JSON, FastAPI would normally return a 422 with
# { "detail": [...] }. After our fix it must return 400 { "error": "..." }.
def test_malformed_json_returns_400_envelope(client):
    res = client.post(
        "/api/posts",
        content="{bad json",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 400
    body = res.json()
    assert "error" in body, f"Expected envelope with 'error' key, got: {body}"
    assert "detail" not in body, f"FastAPI default shape leaked through: {body}"


# A path that doesn't exist should return 404 { "error": "..." }, not the default
# { "detail": "Not Found" }.
def test_unknown_path_returns_404_envelope(client):
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    body = res.json()
    assert "error" in body, f"Expected envelope with 'error' key, got: {body}"
    assert "detail" not in body, f"FastAPI default shape leaked through: {body}"
