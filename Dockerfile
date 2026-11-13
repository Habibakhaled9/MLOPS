FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.3 /uv /uvx /bin/

ENV UV_PYTHON_DOWNLOADS=0 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project


FROM python:3.13-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME="/home/app"

RUN groupadd --system --gid 10001 app \
    && useradd --system \
        --uid 10001 \
        --gid 10001 \
        --create-home \
        --home-dir /home/app \
        app

WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app app ./app
COPY --chown=app:app alembic.ini ./alembic.ini
COPY --chown=app:app migrations ./migrations

RUN mkdir -p /app/logs \
    && chown -R app:app /app/logs

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]