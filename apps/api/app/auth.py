"""API-key auth + per-workspace plans & quotas (Phase 2).

Dev-friendly: body.workspace still works, but if X-API-Key header is
present it wins. Master key can manage everything.
"""
import secrets
from fastapi import Header, HTTPException

from app.config import settings

PLANS = {
    "free": {"messages": 100, "docs": 20, "price_inr": 0, "price_usd": 0},
    "pro": {"messages": 5000, "docs": 1000, "price_inr": 49900, "price_usd": 2900},  # paise/cents
    "scale": {"messages": 50000, "docs": 10000, "price_inr": 249900, "price_usd": 9900},
}

# key -> {workspace, plan}
_keys: dict[str, dict] = {}
# workspace -> plan
_workspace_plans: dict[str, str] = {}


def get_plan(workspace: str) -> str:
    return _workspace_plans.get(workspace, "free")


def set_plan(workspace: str, plan: str):
    if plan not in PLANS:
        raise ValueError(f"unknown plan {plan}")
    _workspace_plans[workspace] = plan
    for k, v in _keys.items():
        if v["workspace"] == workspace:
            v["plan"] = plan


def create_key(workspace: str, plan: str = "free") -> str:
    if plan not in PLANS:
        plan = "free"
    _workspace_plans.setdefault(workspace, plan)
    key = f"cb_{workspace}_{secrets.token_urlsafe(16)}"
    _keys[key] = {"workspace": workspace, "plan": _workspace_plans[workspace]}
    return key


def resolve_workspace(workspace: str = "demo", x_api_key: str | None = None) -> tuple[str, str]:
    """Return (workspace, plan). Raises 401 on bad key."""
    if x_api_key:
        if x_api_key == settings.master_api_key:
            return workspace, get_plan(workspace)
        info = _keys.get(x_api_key)
        if not info:
            raise HTTPException(status_code=401, detail="invalid API key")
        return info["workspace"], info["plan"]
    return workspace, get_plan(workspace)


def optional_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str | None:
    return x_api_key
