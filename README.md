
# Controle Financeiro

Aplicação Streamlit para gerenciar lançamentos financeiros mensais por ano.

**Funcionalidades**
- Carregamento automático de CSVs por ano em `./csv/{ANO}.csv` (formato despivotado: uma linha por mês/lançamento).
- Editor interativo para adicionar, editar e remover lançamentos.
- Marcação de lançamentos como `Pago` por mês.
- Visualização em tabela com formatação condicional (cores por tipo).
- Gráfico combinado (barras empilhadas por Tipo e Status + média anual por tipo) usando Plotly.
- Ao salvar, os dados são normalizados (despivotados) e escritos em `./csv/{ANO}.csv`.

**Requisitos**
- Python 3.12+
- `uv` (gerenciador/sincronizador de dependências usado no Dockerfile)
- Opcional: Docker e Docker Compose (recomendado para reproduzir o ambiente usado)

O projeto usa `pyproject.toml` para declarar dependências e utiliza a ferramenta `uv` (via imagem ghcr.io/astral-sh/uv) dentro do Dockerfile para sincronizar dependências. Não é necessário `pip`/`requirements.txt` quando se usa o fluxo com `uv`.

**Executando (recomendado — Docker Compose)**

Construa e rode o container (o Dockerfile já executa os comandos `uv` durante o build):

```bash
docker compose up --build
```

A aplicação ficará disponível em http://localhost:8502

**Executando localmente com `uv` (sem Docker)**

Se você preferir executar localmente sem Docker e já tem `uv` disponível no sistema, rode:

```bash
uv sync --frozen --no-install-project --no-dev
uv run streamlit run main.py --server.port=8502 --server.address=0.0.0.0
```

Se não tiver o binário `uv`, você pode usar a imagem oficial para executar os comandos `uv` sem instalar localmente (substitua `$(pwd)` por o caminho do projeto):

```bash
docker run --rm -v "$(pwd)":/app -w /app ghcr.io/astral-sh/uv:latest uv sync --frozen --no-install-project --no-dev
docker run --rm -v "$(pwd)":/app -w /app -p 8502:8502 ghcr.io/astral-sh/uv:latest uv run streamlit run main.py --server.port=8502 --server.address=0.0.0.0
```

Esses comandos espelham o comportamento definido no `Dockerfile` e no `docker-compose.yml`.

**Formato esperado do CSV (despivotado)**
- Colunas: `Data` (dd/mm/AAAA), `Item`, `Tipo`, `Categoria`, `Valor`, `Pago`

Exemplo de linha:

```
01/03/2026,Salário,Receita,Trabalho,5000.00,True
```

**Arquitetura resumida**
- `main.py`: interface Streamlit, lógica de carregamento/pivot/despivot e geração de gráficos.
- `pyproject.toml`: declara as dependências do projeto.
- `Dockerfile`: usa a imagem `ghcr.io/astral-sh/uv:latest` para obter o binário `uv`, sincronizar dependências e expor a aplicação.
- `docker-compose.yml`: serviço `carteira-investimento` para rodar a aplicação com volumes e variáveis de ambiente já configuradas.

**Notas e próximos passos**
- Se deseja, posso gerar um arquivo `uv.lock` ou um `requirements.txt` para facilitar execução sem `uv` (posso também adicionar instruções para instalar `uv` localmente).
- Quer que eu atualize o `pyproject.toml` com descrição e metadados extras, ou gere instruções de deploy no README?

