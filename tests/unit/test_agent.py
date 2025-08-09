from fastapi.testclient import TestClient

from vectras.agents.agent import create_app


def test_agent_fake_openai_response(monkeypatch):
    monkeypatch.setenv("VECTRAS_FAKE_OPENAI", "1")
    app = create_app()
    client = TestClient(app)

    r = client.post("/query", json={"query": "hello"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "FAKE_OPENAI_RESPONSE" in data["response"]
