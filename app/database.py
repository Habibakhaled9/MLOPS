from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import get_settings

_database_engine: AsyncEngine | None = None


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


async def close_database_engine() -> None:
    """Close the database connection pool."""

    global _database_engine

    if _database_engine is not None:
        await _database_engine.dispose()
        _database_engine = None


async def read_question_history(
    limit: int,
) -> list[dict[str, int | str | datetime]]:
    """Read recent questions from PostgreSQL."""

    try:
        engine = get_database_engine()

        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT
                        id,
                        question,
                        answer,
                        model_name,
                        created_at
                    FROM question_history
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )

            return [dict(row) for row in result.mappings()]
    except SQLAlchemyError as exc:
        raise DatabaseError(
            "Failed to read question history."
        ) from exc