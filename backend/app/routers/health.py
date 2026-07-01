# WHAT THIS FILE IS
# Defines the "/api/health" web address (a "route"). Visiting it tells you whether
# the app is running AND whether it can reach the database. WHY: hosting services
# and our own monitoring ping this URL to confirm the app is healthy.

from fastapi import APIRouter

from app import db
from app.responses import fail, ok

# A router groups related routes together; app/main.py plugs it into the app.
router = APIRouter()


# When someone sends a GET request to /api/health, run this function.
@router.get("/api/health")
def health():
    try:
        # Try to reach the database. If it answers, report success with db = True.
        # ok(...) wraps the result as { "data": { "ok": true, "db": true } }.
        return ok({"ok": True, "db": db.db_ping()})
    except Exception as e:  # noqa: BLE001 — any database failure should just mean "unhealthy"
        # If the database can't be reached, report failure with HTTP code 500
        # ("server error"), as { "error": "db unreachable: ..." }.
        return fail(f"db unreachable: {e}", 500)
