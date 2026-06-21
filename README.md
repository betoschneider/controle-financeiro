# Controle Financeiro Pessoal

Um aplicativo web moderno e intuitivo de Controle Financeiro Pessoal desenvolvido com backend **FastAPI** (Python), banco de dados **SQLite** com **Alembic** para migrações, e um frontend interativo e responsivo em **HTML5/Vanilla CSS/JavaScript**.

---

## 🚀 Funcionalidades Principais

1. **Autenticação Segura em Duas Etapas (2FA)**:
   - Migração do sistema de token único estático para login por usuário/senha.
   - Segunda etapa de autenticação (2FA) integrada ao **Google Authenticator** via códigos baseados em tempo (**TOTP**).
   - Tela de criação de conta (novo cadastro) exibindo o QR Code para leitura no aplicativo e a chave de configuração manual.
   - Recuperação de acesso com redefinição de senha validada pelo código TOTP do autenticador.

2. **Gerenciamento de Lançamentos**:
   - Tabela interativa para edição de receitas, despesas, investimentos e reservas.
   - Cálculo automático de saldos reais e projetados em tempo real.
   - Propagação inteligente de valores/lançamentos para os meses seguintes.
   - Replicação automática das estruturas e transações de anos anteriores ao abrir um novo ano fiscal.

3. **Filtros Avançados**:
   - Possibilidade de filtrar os lançamentos exibidos na tabela por **Tipo** (Receita, Despesa, Investimento, Reserva) e por **Categoria** (moradia, lazer, salário, etc., carregadas dinamicamente).

4. **Importação e Exportação de Dados**:
   - **Exportar CSV**: Baixe todos os lançamentos cadastrados no banco de dados com um único clique.
   - **Importar CSV**: Permite carregar dados externos a partir de um arquivo CSV (sobrescrevendo o estado atual de lançamentos com aviso prévio de segurança).

5. **Interface Premium e Reativa**:
   - Layout responsivo baseado em glassmorphism e efeitos visuais modernos.
   - Alternador de **Tema Claro / Escuro** direto no cabeçalho com persistência de preferência no navegador do usuário (`localStorage`).

---

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, Alembic, pyotp, bcrypt.
- **Frontend**: HTML5, Vanilla CSS (com variáveis customizadas para temas), Vanilla JavaScript.
- **Gerenciador de Dependências**: UV.

---

## 📦 Como Executar o Projeto Localmente

### 1. Pré-requisitos

Certifique-se de ter o Python 3.12+ e o gerenciador de pacotes **UV** instalados no seu sistema operacional.
Caso não possua o `uv` instalado, você pode instalá-lo seguindo as instruções oficiais ou via pip:
```bash
pip install uv
```

### 2. Configurando o Ambiente e Banco de Dados

No diretório raiz do projeto, instale as dependências:
```bash
uv sync
```

Aplique as migrações do Alembic para criar as tabelas `users` e `transacoes` no banco de dados SQLite:
```bash
uv run alembic upgrade head
```

### 3. Executando o Servidor

Inicie o servidor de desenvolvimento do FastAPI (o frontend é servido como arquivos estáticos a partir da rota raiz):
```bash
uv run uvicorn backend.app.main:app --reload --port 8520
```

Acesse o sistema no seu navegador em: **`http://127.0.0.1:8520`**.

Ao acessar pela primeira vez, utilize o link **"Criar Conta"** na tela de login para registrar o seu usuário inicial e configurar o seu Google Authenticator.

---

## 🧪 Rodando os Testes Automatizados

Criamos uma suíte completa de testes de integração cobrindo o fluxo de registro, login em duas etapas (TOTP), redefinição de senha, upload/download de dados CSV e logout.

Para rodar os testes:
```bash
uv run python -m backend.tests.test_auth_csv
```
