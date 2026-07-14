FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Cria usuário não-root para rodar a aplicação
RUN adduser -D -h /app app

WORKDIR /app

# Cria diretório data com permissão para o usuário app
RUN mkdir -p /app/data && chown app:app /app/data && chmod 0775 /app/data

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ ./app/

# Garante que os arquivos da aplicação pertencem ao usuário app
RUN chown -R app:app /app/app

USER app

EXPOSE 8520

CMD uv run uvicorn app.main:app --host 0.0.0.0 --port 8520
