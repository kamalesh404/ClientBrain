"""Phase 1 + Phase 2 tests — run with: pytest apps/api/test_api.py -v"""
from fastapi.testclient import TestClient

from app.auth import PLANS, create_key, get_plan
from app import billing, db
from app.rag import chunk_text, retrieve

client = TestClient(__import__("main").app)


def test_chunk_and_retrieve():
    docs = chunk_text("Our timings are 9am-9pm daily in Arcot. We serve meals.", "timings.txt")
    hits = retrieve("What are timings?", docs)
    assert hits and "9am" in hits[0]["text"]


def test_chat_end_to_end():
    r = client.post("/v1/ingest/text", json={
        "workspace": "e2e-demo", "source": "timings.txt",
        "text": "We are open 9am-9pm daily in Arcot."})
    assert r.status_code == 200
    r = client.post("/v1/chat", json={"workspace": "e2e-demo", "message": "What are timings?"})
    assert r.status_code == 200
    assert "9am" in r.json()["answer"]


def test_stats_has_quota():
    r = client.get("/v1/stats", params={"workspace": "e2e-demo"})
    assert r.status_code == 200
    j = r.json()
    assert "quota" in j and "remaining" in j and j["plan"] in PLANS


def test_billing_mock_orders():
    r = client.get("/v1/billing/plans")
    assert "pro" in r.json()["plans"]
    r = client.post("/v1/billing/razorpay/order", json={"workspace": "acme", "plan": "pro"})
    assert r.json()["plan"] == "pro"
    r = client.post("/v1/billing/upgrade", json={"workspace": "acme", "plan": "pro"})
    assert r.json()["active"] is True
    assert get_plan("acme") == "pro"


def test_admin_keys_require_master():
    from app.config import settings
    r = client.post("/v1/admin/keys", json={"workspace": "shop1", "plan": "pro"})
    assert r.status_code == 403
    r = client.post("/v1/admin/keys", json={"workspace": "shop1", "plan": "pro"},
                    headers={"X-API-Key": settings.master_api_key})
    assert r.status_code == 200
    key = r.json()["api_key"]
    # use the key
    r = client.post("/v1/chat", json={"workspace": "ignored", "message": "hi"},
                    headers={"X-API-Key": key})
    assert r.status_code == 200
    assert r.json()["workspace"] == "shop1"


def test_quota_enforced():
    ws = "quota-ws"
    client.post("/v1/billing/upgrade", json={"workspace": ws, "plan": "free"})
    # exhaust by direct usage logging
    for _ in range(PLANS["free"]["messages"] + 1):
        db.log_message(ws, 1)
    r = client.post("/v1/chat", json={"workspace": ws, "message": "hi"})
    assert r.status_code == 402
