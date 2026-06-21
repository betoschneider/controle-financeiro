import os
import secrets
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Response, Cookie, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import pyotp

from . import models, schemas, crud
from .database import engine, get_db

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
    authorization: Optional[str] = None,
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

@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """Cadastra um novo usuário e retorna o segredo para o Google Authenticator."""
    existing_user = crud.get_user_by_username(db, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de usuário já cadastrado."
        )
    user = crud.create_user(db, user_in)
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
    return {"success": True, "message": "Senha redefinida com sucesso."}

@app.post("/api/auth/logout")
def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    """Remove o cookie de sessão do usuário e invalida em memória."""
    if session_token and session_token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_token]
    response.delete_cookie("session_token", path="/")
    return {"message": "Sessão encerrada."}


@app.get("/api/transacoes", response_model=List[schemas.TransacaoResponse])
def listar_transacoes(
    ano: int,
    db: Session = Depends(get_db),
    _token: str = Depends(verificar_autenticacao)
):
    """Busca as transações de um ano específico.
    
    Se o ano for futuro/atual e não tiver dados, replica o ano mais recente do banco (como molde/rascunho),
    mas NÃO salva no banco automaticamente (apenas retorna para exibição).
    Se não houver molde disponível no banco, retorna 12 transações zeradas (uma para cada mês).
    """
    transacoes = crud.get_transacoes_por_ano(db, ano, _token)
    
    # Se não houver transações e for o ano atual ou futuro
    ano_atual_sistema = datetime.now().year
    if not transacoes and ano >= ano_atual_sistema:
        # Busca molde do ano mais recente
        molde_original = crud.get_dados_molde_ano_mais_recente(db, _token)
        if molde_original:
            # Filtra o molde agrupando por item, tipo, categoria para evitar duplicidades caso existam
            # E retorna as transações com o ano atualizado e pago=False (e ID dummy menor que 0)
            dummy_id = -1
            for tx in molde_original:
                transacoes.append(
                    models.Transacao(
                        id=dummy_id,
                        ano=ano,
                        mes=tx.mes,
                        item=tx.item,
                        tipo=tx.tipo,
                        categoria=tx.categoria,
                        valor=tx.valor,
                        pago=False  # Inicializa como previsto/não pago para o futuro
                    )
                )
                dummy_id -= 1
        else:
            # Sem molde no banco, cria 12 linhas zeradas base (uma para cada mês de Jan a Dez)
            dummy_id = -1
            for mes in range(1, 13):
                transacoes.append(
                    models.Transacao(
                        id=dummy_id,
                        ano=ano,
                        mes=mes,
                        item="",
                        tipo="",
                        categoria="",
                        valor=0.0,
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

