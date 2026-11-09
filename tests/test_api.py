import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ollama_client import OllamaConnectionError

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ask_endpoint_with_valid_question(monkeypatch) -> None:
    async def fake_generate_answer(question, settings):
        return "Nginx is a web server and reverse proxy."

    monkeypatch.setattr(
        "app.main.generate_answer",
        fake_generate_answer,
    )

    response = client.post(
        "/ask",
        json={"question": "What is Nginx?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "question": "What is Nginx?",
        "answer": "Nginx is a web server and reverse proxy.",
        "model": "qwen2.5:3b",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": "Hi"},
        {"question": "     "},
        {"question": ["not", "a", "string"]},
    ],
)
def test_ask_endpoint_rejects_invalid_input(payload) -> None:
    response = client.post("/ask", json=payload)

    assert response.status_code == 422


def test_ask_endpoint_when_ollama_is_unavailable(monkeypatch) -> None:
    async def fake_generate_answer(question, settings):
        raise OllamaConnectionError("Ollama is offline.")

    monkeypatch.setattr(
        "app.main.generate_answer",
        fake_generate_answer,
    )

    response = client.post(
        "/ask",
        json={"question": "What is Docker?"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Ollama service is unavailable."
    }