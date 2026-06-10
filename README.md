
# Controle Financeiro

Aplicação Streamlit para gerenciar lançamentos financeiros mensais por ano.

## Funcionalidades

- **Autenticação Simples**: Acesso restrito via modal (`st.dialog`) solicitando um token. O token é configurado na variável `ACCESS_TOKEN` no arquivo `.env` e validado de forma segura contra timing attacks.
- **Editor interativo** para adicionar, editar e remover lançamentos com `st.data_editor`.
- **Carregamento automático** de CSVs por ano em `./csv/{ANO}.csv` (formato despivotado: uma linha por mês/lançamento).
- **Marcação de lançamentos como `Pago`** por mês (checkbox por célula).
- **Métricas em tempo real**: Saldo Atual (efetivado) e Saldo Projetado (previsto), atualizados conforme o mês filtrado.
- **✨ Preencher meses seguintes**: propaga automaticamente os valores do mês selecionado para os meses futuros que estejam zerados ou vazios — ideal para despesas e receitas fixas (aluguel, salário, assinaturas). O botão aparece apenas quando um mês específico está selecionado no filtro.
- **Visualização em tabela** com formatação condicional (cores por tipo: Receita, Despesa, Investimento, Reserva).
- **Gráfico combinado** (barras empilhadas por Tipo e Status + média anual por tipo) usando Plotly.
- Ao salvar, os dados são normalizados (despivotados) e escritos em `./csv/{ANO}.csv`.

## Requisitos

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) (gerenciador de dependências e virtualenvs)
- Opcional: Docker e Docker Compose (recomendado para reproduzir o ambiente)

O projeto usa `pyproject.toml` para declarar dependências e `uv.lock` para travar versões. Não é necessário `pip` ou `requirements.txt`.

## Configuração

Antes de executar o projeto, copie o arquivo `.env.example` para `.env` e defina seu token de acesso:

```bash
cp .env.example .env
```

Edite o arquivo `.env` e configure o token desejado:
```env
ACCESS_TOKEN=seuTokenAqui
```

## Executando

### Docker Compose (recomendado)

Construa e rode o container (o arquivo `.env` será montado automaticamente):

```bash
docker compose up --build
```

A aplicação ficará disponível em **http://localhost:8503**

### Localmente com `uv` (sem Docker)

Se você já tem o `uv` instalado:

```bash
uv sync --frozen --no-install-project --no-dev
uv run streamlit run main.py --server.port=8503 --server.address=0.0.0.0
```

### Localmente via imagem Docker do `uv` (sem instalar `uv`)

```bash
docker run --rm -v "$(pwd)":/app -w /app ghcr.io/astral-sh/uv:latest uv sync --frozen --no-install-project --no-dev
docker run --rm -v "$(pwd)":/app -w /app -p 8503:8503 ghcr.io/astral-sh/uv:latest uv run streamlit run main.py --server.port=8503 --server.address=0.0.0.0
```

## Formato Esperado do CSV

Colunas: `Data` (dd/mm/AAAA), `Item`, `Tipo`, `Categoria`, `Valor`, `Pago`

Exemplo:

```csv
Data,Item,Tipo,Categoria,Valor,Pago
01/03/2026,Salário,Receita,Trabalho,5000.00,True
01/03/2026,Aluguel,Despesa,Moradia,1500.00,True
```

## Arquitetura

| Arquivo | Descrição |
|---|---|
| `main.py` | Interface Streamlit, lógica de carregamento/pivot/despivot, propagação de valores, tela de autenticação e gráficos. |
| `pyproject.toml` | Declaração de dependências e metadados do projeto. |
| `uv.lock` | Lock file com versões exatas das dependências. |
| `Dockerfile` | Imagem baseada em `python:3.12-slim` com `uv` para sincronizar dependências e expor a aplicação na porta 8503. |
| `docker-compose.yml` | Serviço `carteira-investimento` com volumes para `.env`, `csv/` e config do Streamlit. |
| `csv/` | Diretório com os arquivos CSV por ano (ignorado pelo `.gitignore`). |
| `.env` | Arquivo contendo variáveis de ambiente locais, como `ACCESS_TOKEN` (ignorado pelo `.gitignore`). |

