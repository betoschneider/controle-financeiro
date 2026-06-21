FROM python:3.12-slim

# Copia o executável do 'uv' direto da imagem oficial para a nossa imagem atual
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
# Evita que o uv crie um ambiente virtual (.venv) dentro do container, 
# instalando os pacotes direto no escopo global do Python do container.
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

# Instala dependências do sistema necessárias
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia apenas o pyproject.toml primeiro para cache de camadas eficiente
COPY pyproject.toml /app/

# Se você tiver um arquivo uv.lock ou poetry.lock, descomente a linha abaixo 
# para garantir instalações 100% reproduzíveis:
COPY uv.lock /app/

# Instala as dependências listadas no pyproject.toml usando o uv
# O --no-cache garante que a imagem final fique leve
RUN uv pip install --no-cache -r pyproject.toml

# Copia o código da aplicação
COPY . /app

EXPOSE 8000

# Comando padrão para iniciar a API
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]