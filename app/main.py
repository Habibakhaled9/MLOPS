import logging

from fastapi import FastAPI, HTTPException, status

from app.config import get_settings
from app.logging_config import configure_logging
from app.ollama_client import (
    OllamaConnectionError,
    OllamaResponseError,
    generate_answer,
)
from app.schemas import AskRequest, AskResponse, HealthResponse

configure_logging()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM Question API",
    description="An API for sending questions to a local Ollama model.",
    version="0.1.0",
)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
)
def health_check() -> HealthResponse:
    """Return the current health of the API."""

    logger.info("Health check requested")
    return HealthResponse(status="healthy")

@app.post(
    "/ask",
    response_model=AskResponse,
    tags=["Questions"],
)
async def ask_question(request: AskRequest) -> AskResponse:
    """Send a validated question to Ollama."""

    settings = get_settings()

    logger.info(
        "Sending question to Ollama model=%s",
        settings.ollama_model,
    )

    try:
        answer = await generate_answer(request.question, settings)
    except OllamaConnectionError as exc:
        logger.exception("Could not connect to Ollama")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ollama service is unavailable.",
        ) from exc
    except OllamaResponseError as exc:
        logger.exception("Ollama returned an invalid response")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ollama returned an invalid response.",
        ) from exc

    logger.info("Answer received from Ollama")

    return AskResponse(
        question=request.question,
        answer=answer,
        model=settings.ollama_model,
    )