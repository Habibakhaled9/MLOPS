from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.models import QARecord

_database_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class DatabaseError(Exception):
    """Raised when a database operation fails."""


def get_database_engine() -> AsyncEngine:
    """Create the shared database connection pool when first needed."""

    global _database_engine

    if _database_engine is None:
        settings = get_settings()

        if settings.database_url is None:
            raise DatabaseError("DATABASE_URL is not configured.")

        _database_engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
        )

    return _database_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create a reusable asynchronous session factory."""

    global _session_factory

    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_database_engine(),
            expire_on_commit=False,
        )

    return _session_factory


async def find_qa_record(
    question_hash: str,
    model_name: str,
) -> QARecord | None:
    """Find an existing answer for a question and model."""

    try:
        async with get_session_factory()() as session:
            result = await session.execute(
                select(QARecord).where(
                    QARecord.question_hash == question_hash,
                    QARecord.model_name == model_name,
                )
            )
            return result.scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise DatabaseError("Failed to search question records.") from exc


async def create_qa_record(
    *,
    original_question: str,
    normalized_question: str,
    question_hash: str,
    answer: str,
    model_name: str,
) -> QARecord:
    """Store a newly generated question and answer."""

    record = QARecord(
        original_question=original_question,
        normalized_question=normalized_question,
        question_hash=question_hash,
        answer=answer,
        model_name=model_name,
    )

    try:
        async with get_session_factory()() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record
    except SQLAlchemyError as exc:
        raise DatabaseError("Failed to store question record.") from exc


async def read_question_history(limit: int) -> list[QARecord]:
    """Read recent question records from PostgreSQL."""

    try:
        async with get_session_factory()() as session:
            result = await session.execute(
                select(QARecord)
                .order_by(QARecord.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars())
    except SQLAlchemyError as exc:
        raise DatabaseError("Failed to read question history.") from exc


async def close_database_engine() -> None:
    """Close the database connection pool."""

    global _database_engine, _session_factory

    if _database_engine is not None:
        await _database_engine.dispose()
        _database_engine = None
        _session_factory = None