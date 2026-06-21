FROM python:3.12-slim

# Copia o executável do 'uv' direto da imagem oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1
# Garante a instalação no escopo global do Python do container
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

# Instala dependências do sistema necessárias
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de gerência de pacotes primeiro
COPY pyproject.toml uv.lock* /app/

# Instala as dependências usando o uv de forma otimizada
RUN uv pip install --no-cache -e . 2>/dev/null || uv pip install --no-cache -r pyproject.toml 2>/dev/null || uv pip install --no-cache .

# Copia o código da aplicação
COPY . /app

# Nova porta desejada
EXPOSE 8521

# Comando padrão iniciando o Uvicorn na nova porta
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8521"]