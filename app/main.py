import logging

from fastapi import FastAPI

from app.logging_config import configure_logging
from app.schemas import HealthResponse

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