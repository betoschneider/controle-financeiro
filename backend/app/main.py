import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Response, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from . import models, schemas, crud
from .database import engine, get_db

# Garante que as tabelas sejam criadas no SQLite
models.Base.metadata.create_all(bind=engine)

# Carrega variáveis de ambiente
load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "minhasenha123")  # Valor padrão de fallback

app = FastAPI(title="Controle Financeiro API")

# Configuração do CORS para permitir desenvolvimento
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    if not token or token != ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido ou ausente."
        )
    return token

@app.post("/api/auth/login", response_model=schemas.AuthResponse)
def login(auth_req: schemas.AuthRequest, response: Response):
    """Valida o token de acesso e define um cookie de sessão se for bem-sucedido."""
    if auth_req.token == ACCESS_TOKEN:
        # Define o cookie válido por 2 horas (7200 segundos)
        response.set_cookie(
            key="session_token",
            value=ACCESS_TOKEN,
            max_age=7200,
            httponly=False,  # Permite que o JS leia no frontend se necessário
            samesite="lax",
            path="/"
        )
        return schemas.AuthResponse(success=True, message="Autenticado com sucesso.")
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido."
    )

@app.post("/api/auth/logout")
def logout(response: Response):
    """Remove o cookie de sessão do usuário."""
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
    transacoes = crud.get_transacoes_por_ano(db, ano)
    
    # Se não houver transações e for o ano atual ou futuro
    ano_atual_sistema = datetime.now().year
    if not transacoes and ano >= ano_atual_sistema:
        # Busca molde do ano mais recente
        molde_original = crud.get_dados_molde_ano_mais_recente(db)
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
    return crud.bulk_save_transacoes_por_ano(db, ano, transacoes)

# Servir o frontend estático
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
