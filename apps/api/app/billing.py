"""Billing: plans, Razorpay + Stripe order creation, webhooks.

Safe by design: without keys it returns MOCK orders so frontend +
demo flow works end-to-end. With keys it calls real SDKs.
"""
import hashlib
import hmac
import time

from app.auth import PLANS, set_plan
from app.config import settings


def plans() -> dict:
    return PLANS


def _mock_order(workspace: str, plan: str, provider: str) -> dict:
    return {
        "provider": provider, "mock": True,
        "order_id": f"mock_{provider}_{workspace}_{plan}_{int(time.time())}",
        "workspace": workspace, "plan": plan,
        "amount": PLANS[plan],
        "note": "Add RAZORPAY/STRIPE keys in .env for live payments.",
    }


def create_razorpay_order(workspace: str, plan: str) -> dict:
    if plan not in PLANS:
        raise ValueError("unknown plan")
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        return _mock_order(workspace, plan, "razorpay")
    import razorpay
    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    order = client.order.create({
        "amount": PLANS[plan]["price_inr"], "currency": "INR",
        "notes": {"workspace": workspace, "plan": plan},
    })
    return {"provider": "razorpay", "mock": False, **order,
            "workspace": workspace, "plan": plan}


def create_stripe_session(workspace: str, plan: str) -> dict:
    if plan not in PLANS:
        raise ValueError("unknown plan")
    if not settings.stripe_secret_key:
        return _mock_order(workspace, plan, "stripe")
    import stripe
    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price_data": {
            "currency": "usd",
            "product_data": {"name": f"ClientBrain {plan}"},
            "unit_amount": PLANS[plan]["price_usd"] or 100,
        }, "quantity": 1}],
        metadata={"workspace": workspace, "plan": plan},
        success_url="https://example.com/success?ws=" + workspace,
        cancel_url="https://example.com/cancel",
    )
    return {"provider": "stripe", "mock": False, "session_id": session.id,
            "url": session.url, "workspace": workspace, "plan": plan}


def verify_razorpay_signature(body: bytes, signature: str) -> bool:
    if not settings.razorpay_webhook_secret:
        return True  # dev mode
    mac = hmac.new(settings.razorpay_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature)


def activate_subscription(workspace: str, plan: str) -> dict:
    set_plan(workspace, plan)
    return {"workspace": workspace, "plan": plan, "active": True}
