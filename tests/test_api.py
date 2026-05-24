from fastapi.testclient import TestClient

from ui.api import app


def test_health_endpoint():
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_reset_returns_initial_workflow_state():
    client = TestClient(app)

    response = client.post("/api/reset")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_step"] == 0
    assert payload["rejected_step"] == -1
    assert payload["generated_testcases"] == []


def test_config_masks_secret_values(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "secret-value-12345")
    client = TestClient(app)

    response = client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"]["llm"] is True
    assert payload["groq_api_key_masked"].startswith("secret")
    assert "12345" not in payload["groq_api_key_masked"]
