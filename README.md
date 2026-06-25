# Controle Financeiro Pessoal

Aplicativo web de controle financeiro pessoal com duas áreas isoladas dentro da mesma aplicação:

- **Controle Financeiro**: lançamentos mensais, saldos, filtros, gráficos, importação/exportação CSV e autenticação.
- **Carteira de Investimento**: acompanhamento de ativos B3, cotações via Yahoo Finance, metas de alocação, sugestão de aporte, importação/exportação CSV e auditoria.

O projeto usa **FastAPI**, **SQLAlchemy**, **SQLite**, **Alembic** e frontend em **HTML/CSS/JavaScript** sem framework.

---

## Novidades Recentes

- Área de **Carteira de Investimento** integrada como uma seção própria da aplicação, separada dos filtros, métricas e gráficos do Controle Financeiro.
- Tabela de ativos com quantidade, preço atual, total, meta, percentual atual, desvio, ramo e grupo.
- Cotações via `yfinance`, com cache de 1 hora para reduzir chamadas ao Yahoo Finance.
- Gráfico horizontal de **Desvio da Meta** com linha vertical no zero e barras coloridas pela cor do grupo do ativo.
- Linhas das tabelas da carteira coloridas por grupo.
- Simulador de aporte com valor disponível e quantidade de ativos a comprar.
- Sugestão automática priorizando os ativos com maior distância negativa da meta.
- Edição da quantidade sugerida antes da confirmação.
- Confirmação de aporte com checkbox, atualizando as quantidades no banco.
- Importação/exportação CSV da carteira, com aviso de que a importação remove os dados atuais.
- Tabela de auditoria exibida na interface e endpoint `/api/audit-logs`.
- Isolamento por usuário para transações e carteira por `owner_id`.
- Login por usuário/senha com 2FA TOTP e login via Google OAuth.
- Correção do uso de `Authorization: Bearer <token>` nas APIs.
- Assets do frontend com cache-busting `?v=9`.

---

## Funcionalidades

### Autenticação

- Cadastro de usuário com senha.
- Configuração de 2FA via Google Authenticator, com QR Code e chave manual.
- Login em duas etapas: senha e código TOTP.
- Redefinição de senha validada por TOTP.
- Login via Google OAuth por popup.
- Sessão por cookie `session_token` e suporte a header `Authorization`.
- Limite opcional de criação de contas via variável `ACCOUNT_QUOTA`.

### Controle Financeiro

- Tabela interativa para receitas, despesas, investimentos e reservas.
- Filtro por ano e por mês ou ano completo.
- Filtros locais por tipo e categoria.
- Métricas de saldo efetivado e saldo projetado.
- Comparativo percentual do saldo projetado em relação ao mês anterior quando a visão é anual.
- Propagação de valores do mês atual para meses seguintes.
- Replicação automática de estrutura do ano mais recente ao abrir ano atual/futuro sem dados.
- Gráficos de evolução mensal, proporção por categoria e ranking de itens.
- Tema claro/escuro persistido no navegador.
- Importação/exportação CSV de lançamentos.

### Carteira de Investimento

- Seção própria acessada pela aba **Carteira**.
- Métricas:
  - Patrimônio total.
  - Total de ativos monitorados.
  - Soma das metas.
- Consulta de cotação atual via Yahoo Finance.
- Fallback para tickers B3/fracionários, como `PETR4F` e `PETR4.SA`.
- Tabela de ativos ordenada pelo desvio da meta, do menor para o maior.
- Cálculos por ativo:
  - Preço.
  - Total atual.
  - Meta.
  - Percentual atual.
  - Desvio.
- Gráfico horizontal de desvio da meta:
  - Linha vertical no zero.
  - Barras coloridas pelo grupo do ativo.
  - Borda sutil indicando desvio positivo ou negativo.
- Simulador de aporte:
  - Input de valor a investir.
  - Input de quantidade de ativos.
  - Sugestão de cotas para os ativos mais abaixo da meta.
  - Cálculo de total sugerido, sobra e novo desvio após aporte.
  - Edição manual das cotas sugeridas.
  - Checkbox de confirmação antes de atualizar a carteira.
- Importação/exportação CSV da carteira.
- Auditoria de ações relevantes.

### Auditoria

Eventos críticos são registrados em `audit_logs`, incluindo:

- Cadastro.
- Login etapa 1.
- Login completo com 2FA.
- Login via Google.
- Cadastro via Google.
- Reset de senha.
- Logout.
- Importação de carteira.
- Confirmação de aporte.

---

## Formatos CSV

### Lançamentos Financeiros

Cabeçalho esperado:

```csv
Data,Item,Tipo,Categoria,Valor,Pago
```

Exemplo:

```csv
01/01/2026,Salário,Receita,Trabalho,5000,True
01/01/2026,Aluguel,Despesa,Moradia,1500,False
```

Observações:

- A importação substitui os lançamentos existentes do usuário.
- Datas aceitas incluem `DD/MM/YYYY` e `YYYY-MM-DD`.
- `Pago` aceita valores como `True`, `False`, `1`, `0`, `pago` e `efetivado`.

### Carteira de Investimento

Cabeçalho esperado:

```csv
Empresa,Ativo,Quantidade,Meta,Ramo,Grupo
```

Exemplo:

```csv
Empresa,Ativo,Quantidade,Meta,Ramo,Grupo
Petrobras,PETR4F,55,2.5,Commodities e Materiais Básicos,Gigante Cíclica
Sanepar,SAPR4F,26,5.71,Utilidade Pública - Energia e Saneamento,Trio de Ferro
B3,B3SA3F,13,5.71,Financeiro / Seguros e Bolsa,Trio de Ferro
```

Observações:

- A importação da carteira remove os dados atuais da carteira do usuário antes de inserir o CSV.
- Também há suporte interno a cabeçalhos em inglês: `company,ticker,quantity,target,sector,group`.
- `Meta` pode usar ponto ou vírgula como separador decimal.

---

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic.
- **Banco**: SQLite.
- **Autenticação**: bcrypt, pyotp, Google OAuth.
- **Finanças/mercado**: yfinance.
- **Frontend**: HTML5, CSS customizado, JavaScript, Chart.js, FontAwesome.
- **Dependências**: uv.
- **Testes**: pytest.

---

## Estrutura Principal

```text
backend/app/
  main.py          Rotas FastAPI e montagem do frontend
  models.py        Modelos SQLAlchemy
  schemas.py       Schemas Pydantic
  crud.py          Operações de banco
  finance.py       Consulta/cache de cotações

frontend/
  index.html
  css/style.css
  js/app.js        Controle financeiro, auth, CSV e navegação
  js/charts.js     Gráficos do controle financeiro
  js/investments.js Carteira de investimento

alembic/versions/
  ...create_initial_tables.py
  ...add_owner_id_to_transactions.py
  ...add_audit_logs_table.py
  ...add_investment_assets_table.py
```

---

## Como Executar Localmente

### 1. Pré-requisitos

- Python 3.12+
- `uv`

Instalação do `uv`, caso necessário:

```bash
pip install uv
```

### 2. Entrar na pasta correta

Importante: execute os comandos a partir da raiz deste projeto:

```bash
cd /home/beto/projetos/js-controle-financeiro
```

Se o comando for executado em outra pasta, o Python pode não encontrar o pacote `backend` e retornar:

```text
ModuleNotFoundError: No module named 'backend'
```

### 3. Instalar dependências

```bash
uv sync
```

### 4. Aplicar migrations

```bash
uv run alembic upgrade head
```

Por padrão, o app local usa `sqlite:///./controle_financeiro.db`. No Docker, a variável `DATABASE_URL` aponta para `sqlite:///./data/controle_financeiro.db`.

### 5. Rodar o servidor

```bash
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8520
```

Acesse:

```text
http://127.0.0.1:8520
```

Para desenvolvimento com reload:

```bash
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8520
```

---

## Variáveis de Ambiente

Crie/edite `.env` conforme necessário:

```env
ACCOUNT_QUOTA=0
DATABASE_URL=sqlite:///./controle_financeiro.db
```

Notas:

- `ACCOUNT_QUOTA=0` significa sem limite de contas.
- `DATABASE_URL` é opcional no modo local, pois há fallback no código.
- O Google OAuth usa o Client ID configurado na meta tag `google-client-id` em `frontend/index.html`.

---

## Docker

O `docker-compose.yml` monta:

- `./data:/app/data` para persistir SQLite.
- `./frontend:/app/frontend:ro` para refletir mudanças no frontend sem rebuild.

Subir a aplicação:

```bash
mkdir -p ./data
chmod 775 ./data
docker compose up --build -d
```

Acesse:

```text
http://127.0.0.1:8520
```

Parar:

```bash
docker compose down
```

---

## Testes e Validações

Rodar a suíte:

```bash
PYTHONPATH=. uv run pytest -q
```

Verificar sintaxe Python:

```bash
uv run python -m compileall backend/app
```

Verificar sintaxe dos scripts frontend:

```bash
node --check frontend/js/app.js
node --check frontend/js/investments.js
```

---

## Endpoints Principais

### Autenticação

- `POST /api/auth/register`
- `POST /api/auth/login/step1`
- `POST /api/auth/login/step2`
- `POST /api/auth/login/google`
- `POST /api/auth/reset-password`
- `POST /api/auth/logout`

### Controle Financeiro

- `GET /api/transacoes?ano=YYYY`
- `POST /api/transacoes/bulk-save?ano=YYYY`
- `GET /api/transacoes/download`
- `POST /api/transacoes/upload`

### Carteira de Investimento

- `GET /api/investments`
- `GET /api/investments/portfolio`
- `POST /api/investments/upload`
- `GET /api/investments/download`
- `POST /api/investments/contribution`

### Auditoria

- `GET /api/audit-logs`

---

## Observações de Uso

- A aba **Controle Financeiro** e a aba **Carteira** são áreas independentes da mesma aplicação.
- Ao alternar para a carteira, filtros e gráficos do controle financeiro são ocultados.
- O cache das cotações fica em memória; reiniciar o servidor limpa o cache.
- A consulta ao Yahoo Finance depende de conectividade e disponibilidade externa.
- Em caso de cache do navegador, os assets usam versão `?v=9`; incremente em `frontend/index.html` quando fizer deploy de mudanças estáticas.
