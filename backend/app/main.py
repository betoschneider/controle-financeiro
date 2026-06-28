import os
import secrets
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Response, Cookie, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import pyotp
import requests

from . import models, schemas, crud, finance
from .database import engine, get_db
from fastapi.responses import StreamingResponse, JSONResponse
from io import StringIO
import csv

# Garante que as tabelas sejam criadas no SQLite
models.Base.metadata.create_all(bind=engine)

# Carrega variáveis de ambiente
load_dotenv()

app = FastAPI(title="Controle Financeiro API")

# Configuração do CORS para permitir desenvolvimento
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sessões ativas em memória (token -> username)
ACTIVE_SESSIONS = {}

# Dependência para verificar autenticação via Header ou Cookie
def verificar_autenticacao(
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None)
):
    token = None
    
    # Tenta extrair do Header
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    # Se não achar no Header, tenta do Cookie
    elif session_token:
        token = session_token

    if not token or token not in ACTIVE_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido ou ausente."
        )
    return ACTIVE_SESSIONS[token]


def _parse_float(value, default=0.0):
    if value in (None, ""):
        return default
    try:
        return float(str(value).strip().replace("%", "").replace(",", "."))
    except ValueError:
        return default


def _parse_int(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(float(str(value).strip().replace(",", ".")))
    except ValueError:
        return default


def _investment_payload(items):
    enriched = []
    for item in items:
        price = finance.get_quote(item.ticker) or 0.0
        total = round((item.quantity or 0) * price, 2)
        enriched.append({
            "id": item.id,
            "company": item.company,
            "ticker": item.ticker,
            "quantity": item.quantity,
            "target": item.target or 0.0,
            "sector": item.sector or "",
            "group": item.group or "",
            "price": price,
            "total": total,
        })

    portfolio_total = sum(item["total"] for item in enriched)
    for item in enriched:
        current_percent = (item["total"] / portfolio_total * 100) if portfolio_total else 0.0
        item["current_percent"] = round(current_percent, 2)
        item["deviation"] = round(current_percent - item["target"], 2)

    enriched.sort(key=lambda item: item["deviation"])
    target_sum = round(sum(item["target"] for item in enriched), 2)
    return {
        "assets": enriched,
        "metrics": {
            "portfolio_total": round(portfolio_total, 2),
            "asset_count": len(enriched),
            "target_sum": target_sum,
            "negative_deviation_count": len([item for item in enriched if item["deviation"] < 0]),
        },
        "last_updated": datetime.now().isoformat(),
    }

@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """Cadastra um novo usuário e retorna o segredo para o Google Authenticator."""
    existing_user = crud.get_user_by_username(db, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de usuário já cadastrado."
        )
    # Verifica cota de novas contas (se definida)
    try:
        quota = int(os.getenv('ACCOUNT_QUOTA', '0'))
    except Exception:
        quota = 0
    if quota > 0:
        total = crud.count_users(db)
        if total >= quota:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Limite de contas atingido.")

    user = crud.create_user(db, user_in)
    crud.create_audit_log(db, user, 'register', f'Usuário registrado: {user.username}')
    totp = pyotp.TOTP(user.totp_secret)
    totp_uri = totp.provisioning_uri(name=user.username, issuer_name="ControleFinanceiro")
    return schemas.UserResponse(
        id=user.id,
        username=user.username,
        totp_secret=user.totp_secret,
        totp_uri=totp_uri
    )

@app.post("/api/auth/login/step1")
def login_step1(auth_req: schemas.LoginStep1Request, db: Session = Depends(get_db)):
    """Primeira etapa do login: valida usuário e senha."""
    user = crud.get_user_by_username(db, auth_req.username)
    if not user or not crud.verify_password(auth_req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos."
        )
    crud.create_audit_log(db, user, 'login_step1', f'Login etapa1 para {user.username}')
    return {
        "success": True,
        "message": "Senha válida. Prossiga para a autenticação em duas etapas."
    }

@app.post("/api/auth/login/step2")
def login_step2(auth_req: schemas.LoginStep2Request, response: Response, db: Session = Depends(get_db)):
    """Segunda etapa do login: valida o código do Google Authenticator e cria a sessão."""
    user = crud.get_user_by_username(db, auth_req.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado."
        )
    
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(auth_req.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código de autenticação inválido."
        )
    
    # Gera token de sessão seguro
    session_token = secrets.token_hex(32)
    ACTIVE_SESSIONS[session_token] = user.username
    
    # Define o cookie válido por 2 horas (7200 segundos)
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7200,
        httponly=False,  # Permite que o JS leia no frontend se necessário
        samesite="lax",
        path="/"
    )
    crud.create_audit_log(db, user, 'login', f'Login completo para {user.username} (2FA)')

    return {
        "success": True,
        "message": "Autenticado com sucesso.",
        "session_token": session_token
    }

@app.post("/api/auth/reset-password")
def reset_password(req: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """Redefine a senha do usuário exigindo validação via código Google Authenticator."""
    user = crud.get_user_by_username(db, req.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário não encontrado."
        )
        
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(req.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de autenticação inválido para redefinição."
        )
        
    crud.reset_user_password(db, user, req.new_password)
    crud.create_audit_log(db, user, 'reset_password', f'Reset de senha para {user.username}')
    return {"success": True, "message": "Senha redefinida com sucesso."}

@app.post("/api/auth/logout")
def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Remove o cookie de sessão do usuário e invalida em memória."""
    if session_token and session_token in ACTIVE_SESSIONS:
        username = ACTIVE_SESSIONS[session_token]
        # registra audit log se usuário existir
        try:
            db = next(get_db())
            user = crud.get_user_by_username(db, username)
            if user:
                crud.create_audit_log(db, user, 'logout', f'Logout {user.username}')
        except Exception:
            pass
        del ACTIVE_SESSIONS[session_token]
    response.delete_cookie("session_token", path="/")
    return {"message": "Sessão encerrada."}


@app.post("/api/auth/login/google")
def login_google(payload: dict, response: Response, db: Session = Depends(get_db)):
    """Login via Google OAuth. Recebe JSON: { "id_token": "..." }"""
    id_token = payload.get('id_token')
    if not id_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="id_token ausente")

    # Valida token com endpoint do Google
    try:
        r = requests.get('https://oauth2.googleapis.com/tokeninfo', params={'id_token': id_token}, timeout=5)
        if r.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Google inválido")
        info = r.json()
        email = info.get('email')
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Google inválido: sem email")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao validar token Google: {str(e)}")

    user = crud.get_user_by_username(db, email)
    # Se não existir, criar novo usuário (se houver cota)
    if not user:
        try:
            quota = int(os.getenv('ACCOUNT_QUOTA', '0'))
        except Exception:
            quota = 0
        if quota > 0 and crud.count_users(db) >= quota:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Limite de contas atingido.")
        user = crud.create_user_google(db, email)
        crud.create_audit_log(db, user, 'register_oauth', f'Usuário criado via Google: {email}')

    # Cria sessão sem 2FA
    session_token = secrets.token_hex(32)
    ACTIVE_SESSIONS[session_token] = user.username
    response.set_cookie(
        key='session_token', value=session_token, max_age=7200, httponly=False, samesite='lax', path='/'
    )
    crud.create_audit_log(db, user, 'login_oauth', f'Login via Google: {user.username}')
    return {"success": True, "message": "Autenticado via Google.", "session_token": session_token}


# Investimentos endpoints
@app.get("/api/investments")
def get_investments(db: Session = Depends(get_db), username: str = Depends(verificar_autenticacao)):
    items = crud.list_investments(db, username)
    result = [
        {
            "id": i.id,
            "company": i.company,
            "ticker": i.ticker,
            "quantity": i.quantity,
            "target": i.target,
            "sector": i.sector,
            "group": i.group
        }
        for i in items
    ]
    return result


@app.get("/api/investments/portfolio")
def get_investment_portfolio(db: Session = Depends(get_db), username: str = Depends(verificar_autenticacao)):
    items = crud.list_investments(db, username)
    return _investment_payload(items)


@app.post("/api/investments/contribution")
def apply_investment_contribution(
    req: schemas.InvestmentContributionRequest,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao)
):
    purchases = [
        {"ticker": item.ticker.strip(), "quantity": item.quantity}
        for item in req.purchases
        if item.ticker.strip() and item.quantity > 0
    ]
    if not purchases:
        raise HTTPException(status_code=400, detail="Nenhuma compra válida foi informada.")

    updated = crud.update_investment_quantities(db, username, purchases)
    user = crud.get_user_by_username(db, username)
    details = ", ".join([f"{p['ticker']} +{p['quantity']}" for p in purchases])
    crud.create_audit_log(db, user, "investments_contribution", f"Aporte confirmado: {details}")
    return {"success": True, "updated": len(updated), "message": "Aporte confirmado com sucesso."}


@app.post("/api/investments/upload")
def upload_investments(file: UploadFile = File(...), db: Session = Depends(get_db), username: str = Depends(verificar_autenticacao)):
    content = file.file.read().decode('utf-8-sig')
    reader = csv.DictReader(StringIO(content))
    required = {"Empresa", "Ativo", "Quantidade", "Meta", "Ramo", "Grupo"}
    headers = set(reader.fieldnames or [])
    if not required.issubset(headers) and not {"company", "ticker", "quantity", "target", "sector", "group"}.issubset(headers):
        raise HTTPException(
            status_code=400,
            detail="Cabeçalhos inválidos. Use Empresa,Ativo,Quantidade,Meta,Ramo,Grupo."
        )

    assets = []
    for row in reader:
        ticker = (row.get('Ativo') or row.get('ticker') or '').strip().upper()
        if not ticker:
            continue
        assets.append({
            'company': row.get('Empresa') or row.get('company') or '',
            'ticker': ticker,
            'quantity': _parse_int(row.get('Quantidade') or row.get('quantity')),
            'target': _parse_float(row.get('Meta') or row.get('target')),
            'sector': row.get('Ramo') or row.get('sector') or '',
            'group': row.get('Grupo') or row.get('group') or ''
        })

    # Remove existentes e insere novos
    crud.delete_all_investments(db, username)
    created = crud.bulk_create_investments(db, assets, username)
    user = crud.get_user_by_username(db, username)
    crud.create_audit_log(db, user, 'investments_import', f'Carteira importada com {len(created)} ativos')
    return {"message": f"{len(created)} ativos importados."}


@app.get("/api/investments/download")
def download_investments(db: Session = Depends(get_db), username: str = Depends(verificar_autenticacao)):
    items = crud.list_investments(db, username)
    si = StringIO()
    fieldnames = ['Empresa','Ativo','Quantidade','Meta','Ramo','Grupo']
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for i in items:
        writer.writerow({
            'Empresa': i.company,
            'Ativo': i.ticker,
            'Quantidade': i.quantity,
            'Meta': i.target if i.target is not None else '',
            'Ramo': i.sector or '',
            'Grupo': i.group or ''
        })
    output = si.getvalue()
    return StreamingResponse(StringIO(output), media_type='text/csv', headers={"Content-Disposition":"attachment; filename=carteira.csv"})


@app.get("/api/audit-logs")
def get_audit_logs(db: Session = Depends(get_db), username: str = Depends(verificar_autenticacao)):
    logs = crud.list_audit_logs(db, username)
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp,
            "action": log.action,
            "detail": log.detail or "",
        }
        for log in logs
    ]


@app.get("/api/transacoes", response_model=List[schemas.TransacaoResponse])
def listar_transacoes(
    ano: int,
    db: Session = Depends(get_db),
    _token: str = Depends(verificar_autenticacao)
):
    """Busca as transações de um ano específico.
    
    Se o ano for futuro e não tiver dados, usa dezembro do ano anterior como rascunho
    para janeiro do ano selecionado, mas NÃO salva no banco automaticamente.
    Fevereiro a dezembro permanecem zerados na montagem da tabela no frontend.
    """
    transacoes = crud.get_transacoes_por_ano(db, ano, _token)
    
    # Se não houver transações e for um ano futuro
    ano_atual_sistema = datetime.now().year
    if not transacoes and ano > ano_atual_sistema:
        fechamento_ano_anterior = [
            tx for tx in crud.get_transacoes_por_ano(db, ano - 1, _token)
            if tx.mes == 12
        ]

        dummy_id = -1
        for tx in fechamento_ano_anterior:
            transacoes.append(
                models.Transacao(
                    id=dummy_id,
                    ano=ano,
                    mes=1,
                    item=tx.item,
                    tipo=tx.tipo,
                    categoria=tx.categoria,
                    valor=tx.valor,
                    pago=False
                )
            )
            dummy_id -= 1
                
    return transacoes

@app.post("/api/transacoes/bulk-save", response_model=List[schemas.TransacaoResponse])
def salvar_transacoes(
    ano: int,
    transacoes: List[schemas.TransacaoCreate],
    db: Session = Depends(get_db),
    _token: str = Depends(verificar_autenticacao)
):
    """Deleta todas as transações daquele ano e salva a nova lista editada pelo usuário."""
    return crud.bulk_save_transacoes_por_ano(db, ano, transacoes, _token)

@app.get("/api/transacoes/download")
def download_csv(
    db: Session = Depends(get_db),
    _username: str = Depends(verificar_autenticacao)
):
    """Gera um arquivo CSV contendo todos os lançamentos do banco de dados."""
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    # Busca todas as transações, ordenadas por ano, mes, tipo, categoria, item
    user = crud.get_user_by_username(db, _username)
    transacoes = []
    if user:
        transacoes = db.query(models.Transacao).filter(models.Transacao.owner_id == user.id).order_by(
        models.Transacao.ano.desc(),
        models.Transacao.mes.asc(),
        models.Transacao.tipo,
        models.Transacao.categoria,
        models.Transacao.item
        ).all()
    
    stream = io.StringIO()
    writer = csv.writer(stream)
    
    # Cabeçalho: Data,Item,Tipo,Categoria,Valor,Pago
    writer.writerow(["Data", "Item", "Tipo", "Categoria", "Valor", "Pago"])
    
    for tx in transacoes:
        data_str = f"01/{tx.mes:02d}/{tx.ano}"
        pago_str = "True" if tx.pago else "False"
        writer.writerow([data_str, tx.item, tx.tipo, tx.categoria, tx.valor, pago_str])
        
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=transacoes.csv"
    return response

@app.post("/api/transacoes/upload")
def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _username: str = Depends(verificar_autenticacao)
):
    """Faz o upload de um arquivo CSV, deleta todas as transações existentes e insere as novas."""
    import csv
    import io
    
    contents = file.file.read()
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        try:
            decoded = contents.decode("latin1")
        except Exception:
            raise HTTPException(status_code=400, detail="Não foi possível decodificar o arquivo. Certifique-se de que é um CSV válido.")
            
    stream = io.StringIO(decoded)
    try:
        reader = csv.DictReader(stream)
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de CSV inválido.")
        
    headers = reader.fieldnames
    if not headers or not all(h in headers for h in ["Data", "Item", "Tipo", "Categoria", "Valor", "Pago"]):
        raise HTTPException(
            status_code=400,
            detail="Cabeçalhos inválidos. O CSV deve conter as colunas: Data,Item,Tipo,Categoria,Valor,Pago"
        )
        
    novas_transacoes = []
    
    try:
        for idx, row in enumerate(reader):
            data_str = row["Data"].strip()
            try:
                dt = datetime.strptime(data_str, "%d/%m/%Y")
            except ValueError:
                try:
                    dt = datetime.strptime(data_str, "%Y-%m-%d")
                except ValueError:
                    try:
                        dt = datetime.strptime(data_str, "%d-%m-%d")
                    except ValueError:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Formato de data inválido na linha {idx+2}: {data_str}. Use DD/MM/YYYY."
                        )
                        
            try:
                valor = float(row["Valor"].strip())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Valor inválido na linha {idx+2}: {row['Valor']}"
                )
                
            pago_str = row["Pago"].strip().lower()
            pago = pago_str in ["true", "1", "t", "yes", "y", "pago", "efetivado"]
            
            item = row["Item"].strip()
            tipo = row["Tipo"].strip()
            categoria = row["Categoria"].strip()
            
            if item or tipo or categoria:
                db_tx = models.Transacao(
                    ano=dt.year,
                    mes=dt.month,
                    item=item,
                    tipo=tipo,
                    categoria=categoria,
                    valor=valor,
                    pago=pago
                )
                novas_transacoes.append(db_tx)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar CSV: {str(e)}")
        
    # Remove apenas transações do usuário autenticado e atribui owner_id nas novas
    user = crud.get_user_by_username(db, _username)
    if user:
        db.query(models.Transacao).filter(models.Transacao.owner_id == user.id).delete()
        for tx in novas_transacoes:
            tx.owner_id = user.id
        db.add_all(novas_transacoes)
    db.commit()
    
    return {"success": True, "count": len(novas_transacoes), "message": f"{len(novas_transacoes)} lançamentos importados com sucesso."}

# Servir o frontend estático
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
