import logging

from fastapi import FastAPI, HTTPException, Path, Query, status

from app.cache import CacheError, read_cache_value, store_cache_value
from app.config import get_settings
from app.database import DatabaseError, read_question_history
from app.logging_config import configure_logging
from app.ollama_client import (
    OllamaConnectionError,
    OllamaResponseError,
)
from app.question_service import answer_question
from app.schemas import (
    AskRequest,
    AskResponse,
    CacheReadResponse,
    CacheWriteRequest,
    CacheWriteResponse,
    HealthResponse,
    QuestionHistoryItem,
)

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
    """Answer a question using cache, database, or Ollama."""

    settings = get_settings()

    try:
        result = await answer_question(request.question, settings)
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
    except DatabaseError as exc:
        logger.exception("Database operation failed")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc

    return AskResponse(
        question=request.question,
        answer=result.answer,
        model=settings.ollama_model,
        source=result.source,
    )


@app.get(
    "/questions",
    response_model=list[QuestionHistoryItem],
    tags=["Database"],
)
async def get_questions(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[QuestionHistoryItem]:
    """Return recently stored questions from PostgreSQL."""

    try:
        rows = await read_question_history(limit)
    except DatabaseError as exc:
        logger.exception("Failed to read question history")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc

    return [QuestionHistoryItem.model_validate(
        {
            "id": row.id,
            "original_question": row.original_question,
            "answer": row.answer,
            "model_name": row.model_name,
            "created_at": row.created_at,
        }
    )
    for row in rows
]

@app.post(
    "/cache",
    response_model=CacheWriteResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Cache"],
)
async def create_cache_entry(
    request: CacheWriteRequest,
) -> CacheWriteResponse:
    """Store a temporary value in Redis."""

    try:
        await store_cache_value(
            key=request.key,
            value=request.value,
            ttl_seconds=request.ttl_seconds,
        )
    except CacheError as exc:
        logger.exception("Failed to write to Redis")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache is unavailable.",
        ) from exc

    return CacheWriteResponse(
        key=request.key,
        value=request.value,
        ttl_seconds=request.ttl_seconds,
    )


@app.get(
    "/cache/{key}",
    response_model=CacheReadResponse,
    tags=["Cache"],
)
async def get_cache_entry(
    key: str = Path(
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9:_-]+$",
    ),
) -> CacheReadResponse:
    """Read a cached value from Redis."""

    try:
        value = await read_cache_value(key)
    except CacheError as exc:
        logger.exception("Failed to read from Redis")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache is unavailable.",
        ) from exc

    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cache key was not found.",
        )

    return CacheReadResponse(key=key, value=value)