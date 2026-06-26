from fastapi import APIRouter

from app.responses import ok

router = APIRouter()


# GET /api/health — liveness. DB reachability (the `db` field) returns in TM1 once the
# SQLModel engine lands; kept liveness-only here to stay within the TM0 scaffold.
@router.get("/api/health")
def health():
    return ok({"ok": True})
