from datetime import datetime, timezone
import time

from fastapi import APIRouter, Header, Response, status

from app import db
from app.auth import PLANS, resolve_workspace
from app.config import settings

router = APIRouter()
_START_TIME = time.time()


@router.get("/health")
def health():
    uptime = round(time.time() - _START_TIME, 2)
    return {
        "status": "ok",
        "ok": True,
        "service": "clientbrain-api",
        "version": "0.2.0",
        "uptime_seconds": uptime,
        "backend": db.backend(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
def ready(response: Response):
    db_status = db.check_connection()
    is_ready = bool(db_status.get("responsive", False))
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "unavailable",
        "ready": is_ready,
        "service": "clientbrain-api",
        "version": "0.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": db_status,
            "config": {
                "status": "ok",
                "chat_model": settings.chat_model,
                "embed_model": settings.embed_model,
                "workspace_default": settings.workspace_default,
                "billing_enabled": settings.billing_enabled,
            },
        },
    }


@router.get("/stats")
def stats(workspace: str = "demo", x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    ws, plan = resolve_workspace(workspace, x_api_key)
    usage = db.get_usage(ws)
    quota = PLANS[plan]
    return {"workspace": ws, "plan": plan, "backend": db.backend(),
            "usage": usage, "quota": quota,
            "remaining": {"messages": max(0, quota["messages"] - usage["messages"]),
                          "docs": max(0, quota["docs"] - usage["docs"])}}
