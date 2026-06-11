FROM python:3.12-slim

# Instalar certificados e curl para debug
RUN apt-get update && apt-get install -y ca-certificates curl && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Configurar diretório de trabalho
WORKDIR /app

# Copiar arquivos de configuração
COPY pyproject.toml uv.lock ./

# Instalar dependências
RUN uv sync --frozen --no-install-project --no-dev

# Copiar código fonte
COPY . .

# Expor porta
EXPOSE 8520

# Comando para executar
CMD ["uv", "run", "streamlit", "run", "main.py", "--server.port=8520", "--server.address=0.0.0.0"]