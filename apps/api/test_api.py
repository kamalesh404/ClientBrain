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
    j = r.json()
    assert j["ok"] is False
    assert j["error"]["code"] == "PAYMENT_REQUIRED"
    assert "quota exceeded" in j["detail"]


def test_health_endpoints():
    for path in ("/health", "/v1/health"):
        r = client.get(path)
        assert r.status_code == 200
        j = r.json()
        assert j["ok"] is True
        assert j["status"] == "ok"
        assert j["service"] == "clientbrain-api"
        assert j["version"] == "0.2.0"
        assert "uptime_seconds" in j and j["uptime_seconds"] >= 0
        assert j["backend"] in ("memory", "postgres")
        assert "timestamp" in j


def test_readiness_probe_endpoints():
    for path in ("/ready", "/v1/ready"):
        r = client.get(path)
        assert r.status_code == 200
        j = r.json()
        assert j["ready"] is True
        assert j["status"] == "ready"
        assert "checks" in j
        db_check = j["checks"]["database"]
        assert db_check["responsive"] is True
        assert db_check["backend"] in ("memory", "postgres")
        cfg_check = j["checks"]["config"]
        assert cfg_check["status"] == "ok"
        assert "chat_model" in cfg_check
        assert "embed_model" in cfg_check


def test_root_metadata():
    r = client.get("/")
    assert r.status_code == 200
    j = r.json()
    assert j["name"] == "ClientBrain API"
    assert j["health"] == "/v1/health"
    assert j["ready"] == "/v1/ready"


def test_request_id_tracing_headers():
    # Auto-generated request ID
    r = client.get("/health")
    assert "X-Request-ID" in r.headers
    assert r.headers["X-Request-ID"].startswith("req_")
    assert "X-Response-Time" in r.headers
    assert r.headers["X-Response-Time"].endswith("ms")

    # Propagate client-supplied request ID
    custom_id = "trace-custom-xyz-12345"
    r2 = client.get("/health", headers={"X-Request-ID": custom_id})
    assert r2.headers["X-Request-ID"] == custom_id


def test_standardized_error_envelope_404():
    r = client.get("/v1/this-endpoint-does-not-exist")
    assert r.status_code == 404
    j = r.json()
    assert j["ok"] is False
    assert j["error"]["code"] == "NOT_FOUND"
    assert "X-Request-ID" in r.headers
    assert j["error"]["request_id"] == r.headers["X-Request-ID"]
    assert "detail" in j


def test_standardized_error_envelope_validation_422():
    # Missing required message parameter in /v1/chat
    r = client.post("/v1/chat", json={"workspace": "demo"})
    assert r.status_code == 422
    j = r.json()
    assert j["ok"] is False
    assert j["error"]["code"] == "VALIDATION_ERROR"
    assert j["error"]["message"] == "Request validation failed"
    assert isinstance(j["error"]["details"], list)
    assert len(j["error"]["details"]) > 0


def test_standardized_error_envelope_auth_401():
    # Supplying an invalid API key should produce 401 with standardized envelope
    r = client.post(
        "/v1/chat",
        json={"workspace": "demo", "message": "hello"},
        headers={"X-API-Key": "cb_invalid_bogus_key"},
    )
    assert r.status_code == 401
    j = r.json()
    assert j["ok"] is False
    assert j["error"]["code"] == "UNAUTHORIZED"
    assert j["error"]["message"] == "invalid API key"
    assert j["detail"] == "invalid API key"


def test_config_settings_defaults():
    from app.config import settings
    assert settings.workspace_default == "demo"
    assert settings.chat_model != ""
    assert settings.embed_model != ""
    assert isinstance(settings.billing_enabled, bool)
