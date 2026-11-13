import hashlib
import logging
from dataclasses import dataclass
from typing import Literal

from app.cache import CacheError, read_cache_value, store_cache_value
from app.config import Settings
from app.database import create_qa_record, find_qa_record
from app.ollama_client import generate_answer

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnswerResult:
    """Answer returned by the Q&A workflow."""

    answer: str
    source: Literal["cache", "database", "ollama"]


def normalize_question(question: str) -> str:
    """Create a consistent representation of a question."""

    return " ".join(question.casefold().split())


def create_question_hash(normalized_question: str) -> str:
    """Create a stable SHA-256 fingerprint for a question."""

    return hashlib.sha256(
        normalized_question.encode("utf-8")
    ).hexdigest()


def create_cache_key(question_hash: str, model_name: str) -> str:
    """Create a Redis key unique to a question and model."""

    return f"qa:{model_name}:{question_hash}"


async def store_answer_safely(
    cache_key: str,
    answer: str,
    ttl_seconds: int,
) -> None:
    """Write to Redis without breaking the main application."""

    try:
        await store_cache_value(cache_key, answer, ttl_seconds)
    except CacheError:
        logger.warning(
            "Redis write failed; continuing without cache",
            exc_info=True,
        )


async def answer_question(
    question: str,
    settings: Settings,
) -> AnswerResult:
    """Return an answer using Redis, PostgreSQL, then Ollama."""

    normalized_question = normalize_question(question)
    question_hash = create_question_hash(normalized_question)
    cache_key = create_cache_key(
        question_hash,
        settings.ollama_model,
    )

    try:
        cached_answer = await read_cache_value(cache_key)
    except CacheError:
        logger.warning(
            "Redis read failed; continuing without cache",
            exc_info=True,
        )
        cached_answer = None

    if cached_answer is not None:
        logger.info("Answer returned from Redis")
        return AnswerResult(answer=cached_answer, source="cache")

    existing_record = await find_qa_record(
        question_hash,
        settings.ollama_model,
    )

    if existing_record is not None:
        await store_answer_safely(
            cache_key,
            existing_record.answer,
            settings.cache_ttl_seconds,
        )
        logger.info("Answer returned from PostgreSQL")
        return AnswerResult(
            answer=existing_record.answer,
            source="database",
        )

    answer = await generate_answer(question, settings)

    await create_qa_record(
        original_question=question,
        normalized_question=normalized_question,
        question_hash=question_hash,
        answer=answer,
        model_name=settings.ollama_model,
    )

    await store_answer_safely(
        cache_key,
        answer,
        settings.cache_ttl_seconds,
    )

    logger.info("New answer generated and stored")
    return AnswerResult(answer=answer, source="ollama")