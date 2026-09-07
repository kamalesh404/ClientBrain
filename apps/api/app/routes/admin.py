"""Admin: API keys + workspace management. Guard with master key."""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app import db
from app.auth import PLANS, create_key, get_plan
from app.config import settings

router = APIRouter()


class KeyIn(BaseModel):
    workspace: str
    plan: str = "free"


def _require_admin(x_api_key: str | None):
    if x_api_key != settings.master_api_key:
        raise HTTPException(status_code=403, detail="admin only (bad master key)")


@router.post("/admin/keys")
def admin_create_key(body: KeyIn, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _require_admin(x_api_key)
    if body.plan not in PLANS:
        raise HTTPException(status_code=400, detail="unknown plan")
    key = create_key(body.workspace, body.plan)
    return {"workspace": body.workspace, "plan": get_plan(body.workspace), "api_key": key}


@router.get("/admin/workspaces")
def admin_workspace(workspace: str, x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    _require_admin(x_api_key)
    return {"workspace": workspace, "plan": get_plan(workspace), "usage": db.get_usage(workspace)}
