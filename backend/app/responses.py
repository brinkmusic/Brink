from typing import Any

from fastapi.responses import JSONResponse

# Consistent JSON envelope for all /api/* routes: { data } on success, { error } on
# failure. Mirrors the contract the React frontend already expects (was api/_lib/respond.ts).


def ok(data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse({"data": data}, status_code=status)


def fail(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)
