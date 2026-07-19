FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Cria usuário não-root para rodar a aplicação
RUN adduser -D -h /app app

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Cria diretório data/ para o banco SQLite
RUN mkdir -p /app/data

COPY app/ ./app/

# Garante que os arquivos da aplicação e data pertencem ao usuário app
RUN chown -R app:app /app/app /app/data

USER app

EXPOSE 8520

CMD uv run uvicorn app.main:app --host 0.0.0.0 --port 8520
