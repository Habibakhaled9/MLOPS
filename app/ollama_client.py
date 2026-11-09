import httpx

from app.config import Settings


class OllamaConnectionError(Exception):
    """Raised when the API cannot connect to Ollama."""


class OllamaResponseError(Exception):
    """Raised when Ollama returns an invalid response."""


async def generate_answer(
    question: str,
    settings: Settings,
) -> str:
    """Send a question to Ollama and return its answer."""

    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"

    payload = {
        "model": settings.ollama_model,
        "prompt": question,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.ollama_timeout_seconds
        ) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.RequestError as exc:
        raise OllamaConnectionError(
            "Could not connect to Ollama."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaResponseError(
            f"Ollama returned HTTP {exc.response.status_code}."
        ) from exc

    try:
        response_data = response.json()
    except ValueError as exc:
        raise OllamaResponseError(
            "Ollama returned invalid JSON."
        ) from exc

    if not isinstance(response_data, dict):
        raise OllamaResponseError("Ollama returned an invalid response.")

    answer = response_data.get("response")

    if not isinstance(answer, str) or not answer.strip():
        raise OllamaResponseError("Ollama returned an empty answer.")

    return answer.strip()