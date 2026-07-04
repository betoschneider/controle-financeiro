FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

RUN mkdir -p /app/data && chmod 0775 /app/data

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/

EXPOSE 8520

CMD sh -c "uv run python3 scripts/alembic_stamp_head_if_needed.py && uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8520"
