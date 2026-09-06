from fastapi import APIRouter

from app.store import get_usage

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True, "service": "clientbrain-api"}


@router.get("/stats")
def stats(workspace: str = "demo"):
    return get_usage(workspace)
