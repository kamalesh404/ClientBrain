from fastapi import APIRouter, Header

from app import db
from app.auth import PLANS, resolve_workspace

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True, "service": "clientbrain-api", "backend": db.backend()}


@router.get("/stats")
def stats(workspace: str = "demo", x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    ws, plan = resolve_workspace(workspace, x_api_key)
    usage = db.get_usage(ws)
    quota = PLANS[plan]
    return {"workspace": ws, "plan": plan, "backend": db.backend(),
            "usage": usage, "quota": quota,
            "remaining": {"messages": max(0, quota["messages"] - usage["messages"]),
                          "docs": max(0, quota["docs"] - usage["docs"])}}
