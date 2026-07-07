# Controle Financeiro Pessoal

Aplicativo web de controle financeiro pessoal com duas áreas isoladas dentro da mesma aplicação:

- **Controle Financeiro**: lançamentos mensais, saldos, filtros, gráficos, importação/exportação CSV e autenticação.
- **Carteira de Investimento**: acompanhamento de ativos B3, cotações via Yahoo Finance, metas de alocação, sugestão de aporte e importação/exportação CSV.

O projeto usa **FastAPI**, **SQLAlchemy**, **SQLite**, **Alembic** e frontend em **HTML/CSS/JavaScript** sem framework.

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

#### Dashboard de Métricas

Quatro cards exibidos no topo da visão, sempre juntos:

| Card | O que mostra |
|---|---|
| **Saldo Projetado do Mês** | Receitas − demais tipos do mês atual (ou mês filtrado). Inclui delta % vs. mês anterior quando a visão é "Ano Completo". |
| **Saldo Efetivo do Mês** | Igual ao Projetado, mas apenas lançamentos com `pago = true`. |
| **Saldo Total do Ano Projetado** | Soma de todas as receitas − demais tipos considerando os 12 meses do ano. **Não é afetado pelo filtro de mês.** Inclui delta % comparado ao Saldo Total Efetivo do ano anterior. |
| **Saldo Total do Ano Efetivo** | Igual ao anterior, mas apenas valores efetivados. **Não é afetado pelo filtro de mês.** |

O delta % do **Saldo Total do Ano Projetado** é calculado em relação ao **Saldo Total Efetivo do ano anterior**, carregado automaticamente em segundo plano. O tooltip de cada delta exibe os valores de referência para contexto.

#### Gráfico de Evolução Mensal

- Posicionado **acima das métricas**, logo após os controles de navegação.
- Exibe receitas, despesas, investimentos e reservas mês a mês para o ano selecionado.

#### Filtros e Controles

Todos os filtros e ações ficam na mesma barra, acima da tabela:

- **Ano**: seleciona o ano dos lançamentos.
- **Mês**: filtra a visão por mês específico ou mantém "Ano Completo". O filtro de mês **não** afeta os cards de Saldo Total do Ano.
- **Tipo**: filtra as linhas da tabela por Receita, Despesa, Investimento ou Reserva.
- **Categoria**: filtra as linhas da tabela por categoria.
- **+ Adicionar**: insere nova linha em branco no topo da tabela.
- **Propagar**: aparece quando um mês específico está selecionado; preenche meses seguintes com o valor do mês atual (apenas onde o valor for zero).
- **Exportar / Importar CSV**.
- **Salvar**: persiste todos os lançamentos no servidor.

#### Tabela de Lançamentos

- Edição inline de Item, Tipo, Categoria, Valor e status de pago (checkbox).
- Colunas de meses exibidas conforme filtro de Mês selecionado.
- **Cabeçalho do mês atual destacado** com cor de fundo diferenciada e borda inferior.
- Linhas coloridas por tipo (verde = Receita, vermelho = Despesa, azul = Investimento, amarelo = Reserva).
- Exclusão de linha com confirmação.

#### Detalhamento Econômico

Abaixo da tabela, com gráficos de:

- **Proporção por Categoria** (rosca).
- **Ranking de Itens** (barras horizontais).
- Filtro para exibir apenas valores efetivados.
- Seletor de tipo a explodir (Receita, Despesa, Investimento ou Reserva).

#### Outras Funcionalidades

- Propagação de valores do mês atual para meses seguintes.
- Replicação automática de estrutura do ano mais recente ao abrir ano atual/futuro sem dados.
- Tema claro/escuro persistido no navegador, com re-renderização automática dos gráficos.
- Importação/exportação CSV de lançamentos.

---

### Carteira de Investimento

Seção acessada pela aba **Carteira**, isolada dos controles do Controle Financeiro.

#### Métricas

- Patrimônio total.
- Total de ativos monitorados.
- Soma das metas.

#### Tabela de Ativos

- Ativos ordenados pelo desvio da meta (menor para o maior).
- Colunas: Ativo, Empresa, Qtd, Preço atual, Total, Meta, % Atual, Desvio, Ramo, Grupo.
- Linhas coloridas por grupo do ativo.
- Cotações via `yfinance` com cache de 1 hora.
- Fallback para tickers B3/fracionários (ex: `PETR4F` → `PETR4.SA`).

#### Gráfico de Desvio da Meta

- Barras horizontais coloridas pela cor do grupo.
- Linha vertical no zero.
- Borda indicando desvio positivo ou negativo.

#### Simulador de Aporte

- Input de valor a investir e quantidade de ativos.
- Sugestão automática priorizando os ativos com maior distância negativa da meta.
- Edição manual das cotas sugeridas.
- Cálculo de total sugerido, sobra e novo desvio após aporte.
- Checkbox de confirmação antes de atualizar a carteira.

#### CSV

- Importação/exportação CSV da carteira.

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

- A importação substitui todos os lançamentos existentes do usuário.
- Datas aceitas incluem `DD/MM/YYYY` e `YYYY-MM-DD`.
- `Pago` aceita valores como `True`, `False`, `1`, `0`, `pago` e `efetivado`.
- Valores ausentes ou nulos são tratados como `0.0`.

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

- A importação remove os dados atuais da carteira do usuário antes de inserir o CSV.
- Também há suporte a cabeçalhos em inglês: `company,ticker,quantity,target,sector,group`.
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
app/
  main.py               App FastAPI, CORS, Auth Google e mount /static
  config.py             Config (.env), Engine, SessionLocal, Base
  models.py             Modelos SQLAlchemy (unificados)
  transactions.py       Router de transações + settings (tipos/categorias)
  investments.py        Router de investimentos + yfinance
  auth.py               Sessões e autenticação
  static/
    index.html
    carteira-investimento.html
    google_oauth_callback.html
    css/
      style.css
    js/
      app.js
alembic/
  env.py
  versions/
    bb8a7514b4ee_banco_unificado_v1.py   ← migração única (todas as tabelas)
data/
scripts/
  alembic_stamp_head_if_needed.py
  import_csv.py
.env
Dockerfile
docker-compose.yml
pyproject.toml
uv.lock
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

### 2. Entrar na pasta do projeto

Execute os comandos a partir da raiz do projeto:

```bash
cd /home/beto/projetos/controle-financeiro
```

### 3. Instalar dependências

```bash
uv sync
```

### 4. Aplicar migrations

```bash
uv run alembic upgrade head
```

> Por padrão, o app usa `sqlite:///./data/controle_financeiro.db`.
>
> **Nota**: As migrações foram unificadas em um único arquivo (`bb8a7514b4ee_banco_unificado_v1.py`). Se você já possui um banco de dados com migrações antigas, o script `scripts/alembic_stamp_head_if_needed.py` (executado automaticamente no Docker) fará o stamp para a nova head.

### 5. Rodar o servidor

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8520
```

Acesse: `http://127.0.0.1:8520`

Para desenvolvimento com reload automático:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8520
```

---

## Variáveis de Ambiente

Crie ou edite `.env` conforme necessário:

```env
DATABASE_URL=sqlite:///./data/controle_financeiro.db
SECRET_KEY=sua_chave_secreta_aqui
GOOGLE_CLIENT_ID=seu_client_id_aqui
QUOTE_CACHE_TTL=3600
ACCOUNT_QUOTA=0
```

Notas:

- `ACCOUNT_QUOTA=0` significa sem limite de criação de contas. Qualquer valor positivo limita o número máximo de usuários.
- `DATABASE_URL` é opcional no modo local; há fallback no código.
- `GOOGLE_CLIENT_ID` é usado no login Google OAuth.
- `QUOTE_CACHE_TTL` define o cache de cotações do `yfinance` em segundos.

---

## Docker

O `docker-compose.yml` monta:

- `./data:/app/data` para persistir o SQLite.

Subir a aplicação:

```bash
mkdir -p ./data
chmod 775 ./data
docker compose up --build -d
```

Acesse: `http://127.0.0.1:8520`

Parar:

```bash
docker compose down
```

---

## Testes e Validações

Rodar a suíte de testes:

```bash
PYTHONPATH=. uv run pytest -q
```

Verificar sintaxe Python:

```bash
uv run python -m compileall app
```

---

## Endpoints Principais

### Autenticação

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/auth/register` | Cadastro de usuário |
| `POST` | `/api/auth/login/step1` | Login etapa 1 (senha) |
| `POST` | `/api/auth/login/step2` | Login etapa 2 (TOTP) |
| `POST` | `/api/auth/login/google` | Login via Google OAuth |
| `POST` | `/api/auth/reset-password` | Redefinição de senha |
| `POST` | `/api/auth/logout` | Logout |

### Controle Financeiro

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/transactions?ano=YYYY` | Lista lançamentos do ano |
| `POST` | `/api/transactions/bulk-save?ano=YYYY` | Salva todos os lançamentos do ano |
| `GET` | `/api/transactions/anos` | Lista anos com lançamentos |
| `GET` | `/api/transactions/download` | Exporta CSV completo |
| `POST` | `/api/transactions/upload` | Importa CSV (substitui dados) |
| `GET` | `/api/transactions/dropdown-data` | Tipos e categorias para dropdowns |
| `GET` | `/api/transactions/dashboard/categoria-comparativo` | Comparativo categorias vs metas |

### Configurações (Tipos e Categorias)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/settings/tipos` | Lista tipos (Receita, Despesa...) |
| `POST` | `/api/settings/tipos` | Cria novo tipo |
| `PUT` | `/api/settings/tipos/{id}` | Altera nome do tipo |
| `DELETE` | `/api/settings/tipos/{id}` | Remove tipo (se não protegido) |
| `GET` | `/api/settings/categorias` | Lista categorias do usuário |
| `POST` | `/api/settings/categorias` | Cria nova categoria |
| `PUT` | `/api/settings/categorias/{id}` | Altera categoria |
| `DELETE` | `/api/settings/categorias/{id}` | Remove categoria (se não protegida) |

### Carteira de Investimento

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/investments` | Lista ativos da carteira |
| `GET` | `/api/investments/portfolio` | Dados com cotações e cálculos |
| `POST` | `/api/investments/upload` | Importa CSV da carteira |
| `GET` | `/api/investments/download` | Exporta CSV da carteira |
| `POST` | `/api/investments/contribution` | Confirma aporte sugerido |

---

## Observações de Uso

- A aba **Controle Financeiro** e a aba **Carteira** são áreas independentes; ao alternar, filtros e gráficos da outra área são ocultados.
- Os cards **Saldo Total do Ano** sempre refletem o ano inteiro, independentemente do filtro de mês selecionado.
- O comparativo % do **Saldo Total do Ano Projetado** é calculado em relação ao Saldo Total Efetivo do ano anterior, carregado em background após o carregamento principal.
- O cache das cotações fica em memória; reiniciar o servidor limpa o cache.
- A consulta ao Yahoo Finance depende de conectividade e disponibilidade externa.
- Em caso de cache do navegador, os assets usam versão `?v=14`; incremente em `app/static/index.html` ao fazer deploy de mudanças estáticas.

---

## 🔒 Ajustes de Segurança Implementados

### Vulnerabilidades Críticas Corrigidas

1. **Chave Secreta Padrão**: Removido o valor padrão `"change-me"` da `SECRET_KEY`. Agora, a aplicação exige que a `SECRET_KEY` seja configurada via variável de ambiente.

2. **Cookie de Sessão sem `HttpOnly`**: Corrigido para definir `httponly=True` em todos os cookies de sessão, prevenindo ataques XSS.

3. **CORS Permissivo**: Restringido `allow_origins` apenas aos domínios confiáveis, prevenindo ataques CSRF.

4. **Exposição de `totp_secret`**: Removido `totp_secret` da resposta de registro, evitando exposição de dados sensíveis.

### Vulnerabilidades Importantes Corrigidas

1. **Gerenciamento de Sessão em Memória**: Adicionado comentário indicando a necessidade de implementar um sistema robusto de gerenciamento de sessão com armazenamento persistente (Redis, PostgreSQL).

2. **Falta de Validação de `GOOGLE_CLIENT_ID`**: Implementada validação do `aud` (audience) no token Google para garantir que o token seja emitido para a aplicação correta.

3. **Falta de Limite de Taxa para Tentativas de Login**: Adicionado comentário indicando a necessidade de implementar um mecanismo de limite de taxa para evitar ataques de força bruta.

4. **Falta de Validação de Entrada no Nível do Modelo**: Adicionados limites de comprimento para os campos `item`, `tipo` e `categoria` no modelo `Transacao`.

### Boas Práticas de Segurança

- **Hash de Senha com `bcrypt`**: As funções `hash_password` e `verify_password` utilizam `bcrypt`, que é um algoritmo de hash de senha robusto e recomendado.
- **Autenticação de Dois Fatores (2FA) com TOTP**: A implementação de TOTP com `pyotp` para registro, login de dois passos e redefinição de senha é uma boa adição de segurança.
- **Validação de Entrada com Pydantic**: O uso de `BaseModel` do Pydantic para validar a entrada das requisições é uma boa prática.
- **Quota de Contas**: A implementação de `ACCOUNT_QUOTA` ajuda a prevenir ataques de esgotamento de recursos.

### Próximos Passos Recomendados

1. **Implementar um sistema robusto de gerenciamento de sessão**: Utilizar armazenamento persistente (Redis, PostgreSQL) para sessões.
2. **Implementar limites de taxa**: Utilizar bibliotecas como `slowapi` ou `fastapi-limiter` para evitar ataques de força bruta.
3. **Revisar e testar**: Garantir que todas as alterações estejam funcionando corretamente.

---

## 📚 Recursos Adicionais

- [OWASP Top 10](https://owasp.org/www-project-top-ten/): Lista das 10 vulnerabilidades de segurança mais críticas em aplicações web.
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/): Documentação oficial do FastAPI sobre segurança.
- [CORS MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS): Documentação sobre CORS e como configurá-lo corretamente.
- [bcrypt](https://pypi.org/project/bcrypt/): Documentação da biblioteca `bcrypt` para hash de senhas.
- [pyotp](https://pypi.org/project/pyotp/): Documentação da biblioteca `pyotp` para autenticação de dois fatores.
