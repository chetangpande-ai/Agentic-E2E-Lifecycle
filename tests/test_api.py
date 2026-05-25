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


def test_latest_log_prefers_application_log(tmp_path, monkeypatch):
    import ui.api as api_module

    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    local_log = logs_dir / "local-backend.out.log"
    app_log = logs_dir / "agentic_qe_20260525.log"
    local_log.write_text("local server noise", encoding="utf-8")
    app_log.write_text("workflow detail", encoding="utf-8")
    monkeypatch.setattr(api_module, "ROOT", tmp_path)

    client = TestClient(app)
    response = client.get("/api/logs/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == app_log.name
    assert payload["content"] == "workflow detail"
