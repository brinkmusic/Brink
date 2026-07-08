# WHAT THIS FILE IS
# The starting point of the backend. It creates the app, plugs in the routes, and
# registers error handlers. WHY it's tiny: the actual routes live in separate
# files under routers/, and this file just wires them together. When you run the
# server, it loads "app" from here.
#
# ERROR HANDLING RULE: every response — success or failure — uses the { "data": ... }
# or { "error": ... } envelope from responses.py. The three handlers below make sure
# even FastAPI's built-in errors (bad request bodies, unknown paths) use that same
# shape instead of FastAPI's default { "detail": ... } format (ADR-0010, ADR-0007 §1).

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import verify_required_settings
from app.deps import AuthError
from app.rate_limit import RateLimitError
from app.responses import fail
from app.routers import auth, comments, health, posts, reactions


# Runs once when the server boots (and shuts down). We use it to fail fast on missing
# secrets: a misdeployed instance crashes here instead of serving 500s per request.
# In tests this never fires (the TestClient isn't used as a context manager) and the
# check has its own pytest escape hatch anyway — see config.verify_required_settings.
@asynccontextmanager
async def lifespan(app: FastAPI):
    verify_required_settings()
    yield


app = FastAPI(title="Brink API", lifespan=lifespan)

app.include_router(health.router)  # GET /api/health
app.include_router(auth.router)    # POST /api/auth/capture-spotify
app.include_router(posts.router)   # POST /api/posts, GET /api/posts?userId=
app.include_router(reactions.router)  # POST/DELETE /api/posts/{id}/reactions
app.include_router(comments.router)   # POST/GET /api/posts/{id}/comments


# Auth failures (e.g. missing or invalid session token) → 401 { "error": ... }.
@app.exception_handler(AuthError)
def _handle_auth_error(request: Request, exc: AuthError):
    return fail(exc.message, exc.status)


# Rate-limit refusals → 429 { "error": ... }. Same envelope shape as every other error.
@app.exception_handler(RateLimitError)
def _handle_rate_limit_error(request: Request, exc: RateLimitError):
    return fail(exc.message, exc.status)


# Malformed or wrongly-typed request bodies → 400 { "error": ... }.
# Without this, FastAPI returns 422 { "detail": [...] } which the frontend can't parse.
# NOTE FOR T10+: declare required, typed fields in request schemas — don't copy
# capture-spotify's all-Optional workaround. This handler gives those a clean 400.
@app.exception_handler(RequestValidationError)
def _handle_validation_error(request: Request, exc: RequestValidationError):
    return fail("invalid request", 400)


# Unknown paths (404) and method-not-allowed (405) → { "error": ... }.
# Catches starlette.exceptions.HTTPException, which FastAPI uses internally for routing
# errors; fastapi.HTTPException (raised by route code) is a subclass so it's caught too.
@app.exception_handler(StarletteHTTPException)
def _handle_http_error(request: Request, exc: StarletteHTTPException):
    return fail(exc.detail, exc.status_code)
