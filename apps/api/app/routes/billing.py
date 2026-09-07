from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import billing

router = APIRouter()


class OrderIn(BaseModel):
    workspace: str = "demo"
    plan: str = "pro"


@router.get("/billing/plans")
def get_plans():
    return {"plans": billing.plans()}


@router.post("/billing/razorpay/order")
def razorpay_order(body: OrderIn):
    return billing.create_razorpay_order(body.workspace, body.plan)


@router.post("/billing/stripe/session")
def stripe_session(body: OrderIn):
    return billing.create_stripe_session(body.workspace, body.plan)


@router.post("/billing/upgrade")
def manual_upgrade(body: OrderIn):
    """Dev/admin path: activate without payment (tests, demos)."""
    return billing.activate_subscription(body.workspace, body.plan)


@router.post("/billing/webhook/razorpay")
async def razorpay_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")
    if not billing.verify_razorpay_signature(body, sig):
        return {"ok": False, "error": "bad signature"}
    data = await request.json() if body else {}
    try:
        notes = data.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {})
        ws, plan = notes.get("workspace", "demo"), notes.get("plan", "pro")
    except Exception:
        ws, plan = "demo", "pro"
    return {"ok": True, **billing.activate_subscription(ws, plan)}


@router.post("/billing/webhook/stripe")
async def stripe_webhook(request: Request):
    # Full signature verify needs stripe SDK + endpoint secret; accept metadata in dev.
    try:
        data = await request.json()
        md = data.get("data", {}).get("object", {}).get("metadata", {}) or data.get("metadata", {})
        ws, plan = md.get("workspace", "demo"), md.get("plan", "pro")
    except Exception:
        ws, plan = "demo", "pro"
    return {"ok": True, **billing.activate_subscription(ws, plan)}
