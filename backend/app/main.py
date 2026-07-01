# WHAT THIS FILE IS
# The starting point of the backend. It creates the app, plugs in the routes, and
# registers one error handler. WHY it's tiny: the actual routes live in separate
# files under routers/, and this file just wires them together. When you run the
# server, it loads "app" from here.

from fastapi import FastAPI, Request

from app.deps import AuthError
from app.responses import fail
from app.routers import auth, health

app = FastAPI(title="Brink API")

app.include_router(health.router)  # GET /api/health
app.include_router(auth.router)    # POST /api/auth/capture-spotify


# When any auth check raises AuthError, turn it into our standard { "error": ... }
# response with the right status code (e.g. 401), instead of FastAPI's default shape.
@app.exception_handler(AuthError)
def _handle_auth_error(request: Request, exc: AuthError):
    return fail(exc.message, exc.status)
