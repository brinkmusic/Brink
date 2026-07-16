# WHAT THIS FILE IS
# Two small helpers that shape every API response the same way, so any caller
# (the browser JavaScript in app/static/, the tests, or a future client) always
# knows what to expect:
#   - success looks like:  { "data": ... }
#   - failure looks like:  { "error": "some message" }
# WHY: a consistent "envelope" means callers have one rule for reading results.

from typing import Any

from fastapi.responses import JSONResponse


# Wrap a successful result. `status` is the HTTP code (200 = OK by default).
def ok(data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse({"data": data}, status_code=status)


# Wrap an error. `status` is the HTTP code (400 = bad request by default).
def fail(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)
