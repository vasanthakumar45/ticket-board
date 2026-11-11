from app import app


def test_health():
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "UP"


def test_version():
    client = app.test_client()
    response = client.get("/api/version")
    assert response.status_code == 200
    assert response.get_json()["version"] == "v1"


def test_ticket_needs_title():
    client = app.test_client()
    response = client.post("/api/tickets", json={})
    assert response.status_code == 400


def test_ticket_rejects_bad_priority():
    client = app.test_client()
    response = client.post("/api/tickets", json={"title": "Printer down", "priority": "urgent"})
    assert response.status_code == 400
