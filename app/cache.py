from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import get_settings


class CacheError(Exception):
    """Raised when a Redis operation fails."""


async def store_cache_value(
    key: str,
    value: str,
    ttl_seconds: int,
) -> None:
    """Store a value in Redis with an expiration time."""

    settings = get_settings()

    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    try:
        await client.set(
            name=key,
            value=value,
            ex=ttl_seconds,
        )
    except RedisError as exc:
        raise CacheError("Failed to write to Redis.") from exc
    finally:
        await client.aclose()


async def read_cache_value(key: str) -> str | None:
    """Read a value from Redis."""

    settings = get_settings()

    client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    try:
        return await client.get(key)
    except RedisError as exc:
        raise CacheError("Failed to read from Redis.") from exc
    finally:
        await client.aclose()