"""
Integration tests for SupportLens API.

All tests use the `client` fixture (see conftest.py) which provides a
FastAPI TestClient backed by an isolated in-memory SQLite database.
LLM calls are mocked so tests never hit Ollama.
"""
from unittest.mock import AsyncMock, patch

import pytest


# ── Health ────────────────────────────────────────────────────────────────────


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "service" in body
    assert "uptime_seconds" in body
    assert "dependencies" in body
    assert isinstance(body["dependencies"], dict)
    assert isinstance(body["uptime_seconds"], int)
    assert body["uptime_seconds"] >= 0


def test_health_status_vocabulary(client):
    resp = client.get("/health")
    assert resp.json()["status"] in ("healthy", "degraded", "unhealthy")


def test_health_database_dep_present(client):
    deps = client.get("/health").json()["dependencies"]
    assert "database" in deps
    assert deps["database"]["status"] in ("healthy", "unhealthy")


def test_health_ollama_dep_present(client):
    deps = client.get("/health").json()["dependencies"]
    assert "ollama" in deps
    assert deps["ollama"]["status"] in ("healthy", "degraded", "unavailable")


# ── Analytics ─────────────────────────────────────────────────────────────────


def test_analytics_empty_db(client):
    resp = client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_traces"] == 0
    assert body["average_response_time"] == 0.0
    assert body["breakdown"] == []


# ── Traces — validation ───────────────────────────────────────────────────────


def test_create_trace_rejects_empty_message(client):
    resp = client.post("/api/v1/traces/", json={"user_message": ""})
    assert resp.status_code == 422


def test_create_trace_rejects_message_too_long(client):
    resp = client.post("/api/v1/traces/", json={"user_message": "x" * 2001})
    assert resp.status_code == 422


def test_create_trace_rejects_missing_body(client):
    resp = client.post("/api/v1/traces/", json={})
    assert resp.status_code == 422


def test_list_traces_empty(client):
    resp = client.get("/api/v1/traces/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_traces_invalid_category_filter(client):
    resp = client.get("/api/v1/traces/?category=NotACategory")
    assert resp.status_code == 422


def test_get_trace_not_found(client):
    resp = client.get("/api/v1/traces/does-not-exist")
    assert resp.status_code == 404


def test_delete_trace_not_found(client):
    resp = client.delete("/api/v1/traces/does-not-exist")
    assert resp.status_code == 404


# ── Traces — happy path (LLM mocked) ─────────────────────────────────────────


@patch("app.routers.traces.generate_bot_response", new_callable=AsyncMock)
@patch("app.routers.traces.classify_trace", new_callable=AsyncMock)
def test_create_trace_success(mock_classify, mock_generate, client):
    mock_generate.return_value = "You were charged because of a mid-cycle upgrade."
    mock_classify.return_value = "Billing"

    resp = client.post(
        "/api/v1/traces/",
        json={"user_message": "Why was I charged $20 extra?"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user_message"] == "Why was I charged $20 extra?"
    assert body["bot_response"] == "You were charged because of a mid-cycle upgrade."
    assert body["category"] == "Billing"
    assert "id" in body
    assert "timestamp" in body
    assert isinstance(body["response_time_ms"], int)


@patch("app.routers.traces.generate_bot_response", new_callable=AsyncMock)
@patch("app.routers.traces.classify_trace", new_callable=AsyncMock)
def test_create_trace_appears_in_list(mock_classify, mock_generate, client):
    mock_generate.return_value = "We'll process your refund within 5 days."
    mock_classify.return_value = "Refund"

    client.post("/api/v1/traces/", json={"user_message": "I want a refund."})

    list_resp = client.get("/api/v1/traces/")
    assert list_resp.status_code == 200
    traces = list_resp.json()
    assert len(traces) == 1
    assert traces[0]["category"] == "Refund"


@patch("app.routers.traces.generate_bot_response", new_callable=AsyncMock)
@patch("app.routers.traces.classify_trace", new_callable=AsyncMock)
def test_list_traces_category_filter(mock_classify, mock_generate, client):
    mock_generate.return_value = "Sure, I can help with that."
    mock_classify.return_value = "Billing"
    client.post("/api/v1/traces/", json={"user_message": "Invoice question"})

    mock_classify.return_value = "Refund"
    client.post("/api/v1/traces/", json={"user_message": "Refund please"})

    billing_resp = client.get("/api/v1/traces/?category=Billing")
    assert billing_resp.status_code == 200
    billing = billing_resp.json()
    assert len(billing) == 1
    assert billing[0]["category"] == "Billing"


@patch("app.routers.traces.generate_bot_response", new_callable=AsyncMock)
@patch("app.routers.traces.classify_trace", new_callable=AsyncMock)
def test_get_trace_by_id(mock_classify, mock_generate, client):
    mock_generate.return_value = "Thanks for contacting us."
    mock_classify.return_value = "General Inquiry"

    create_resp = client.post(
        "/api/v1/traces/", json={"user_message": "Just browsing."}
    )
    trace_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/traces/{trace_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == trace_id


@patch("app.routers.traces.generate_bot_response", new_callable=AsyncMock)
@patch("app.routers.traces.classify_trace", new_callable=AsyncMock)
def test_delete_trace(mock_classify, mock_generate, client):
    mock_generate.return_value = "Done."
    mock_classify.return_value = "Cancellation"

    create_resp = client.post(
        "/api/v1/traces/", json={"user_message": "Cancel my account."}
    )
    trace_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/v1/traces/{trace_id}")
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/v1/traces/{trace_id}")
    assert get_resp.status_code == 404


@patch("app.routers.traces.generate_bot_response", new_callable=AsyncMock)
@patch("app.routers.traces.classify_trace", new_callable=AsyncMock)
def test_analytics_after_traces(mock_classify, mock_generate, client):
    mock_generate.return_value = "Here to help."
    mock_classify.return_value = "Billing"
    client.post("/api/v1/traces/", json={"user_message": "Invoice question"})
    mock_classify.return_value = "Refund"
    client.post("/api/v1/traces/", json={"user_message": "Refund please"})

    resp = client.get("/api/v1/analytics/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_traces"] == 2
    assert body["average_response_time"] >= 0
    categories = [b["category"] for b in body["breakdown"]]
    assert "Billing" in categories
    assert "Refund" in categories


@patch("app.routers.traces.generate_bot_response", new_callable=AsyncMock)
def test_create_trace_llm_empty_returns_503(mock_generate, client):
    mock_generate.return_value = ""

    resp = client.post(
        "/api/v1/traces/", json={"user_message": "Hello?"}
    )
    assert resp.status_code == 503


# ── Tickets ───────────────────────────────────────────────────────────────────


def test_list_tickets_empty(client):
    resp = client.get("/api/v1/tickets/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_ticket(client):
    resp = client.post(
        "/api/v1/tickets/",
        json={"title": "Can't login", "description": "Getting 401 on login page"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Can't login"
    assert body["status"] == "open"
    assert "id" in body


def test_get_ticket(client):
    create_resp = client.post(
        "/api/v1/tickets/",
        json={"title": "Billing query", "description": "Overcharged last month"},
    )
    tid = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/tickets/{tid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == tid


def test_get_ticket_not_found(client):
    resp = client.get("/api/v1/tickets/99999")
    assert resp.status_code == 404


def test_update_ticket_status(client):
    create_resp = client.post(
        "/api/v1/tickets/",
        json={"title": "Open issue", "description": "Details here"},
    )
    tid = create_resp.json()["id"]

    patch_resp = client.patch(f"/api/v1/tickets/{tid}", json={"status": "resolved"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "resolved"


def test_delete_ticket(client):
    create_resp = client.post(
        "/api/v1/tickets/",
        json={"title": "To delete", "description": "Will be gone"},
    )
    tid = create_resp.json()["id"]

    del_resp = client.delete(f"/api/v1/tickets/{tid}")
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/v1/tickets/{tid}")
    assert get_resp.status_code == 404


def test_ticket_list_grows(client):
    for i in range(3):
        client.post(
            "/api/v1/tickets/",
            json={"title": f"Ticket {i}", "description": "desc"},
        )
    resp = client.get("/api/v1/tickets/")
    assert len(resp.json()) == 3
