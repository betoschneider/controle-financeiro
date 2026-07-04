import os
from typing import Optional

import bcrypt
import pyotp
import requests
from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import investments, models, transactions
from app.auth import criar_sessao, encerrar_sessao, verificar_autenticacao
from app.config import engine, get_db
from app.models import User
from app.transactions import get_user_by_username


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def count_users(db: Session) -> int:
    return db.query(User).count()


def create_user(db: Session, username: str, password: str) -> User:
    db_user = User(
        username=username.strip(),
        password_hash=hash_password(password),
        totp_secret=pyotp.random_base32(),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_user_google(db: Session, username: str) -> User:
    random_pw = bcrypt.gensalt()
    hashed = bcrypt.hashpw(random_pw, bcrypt.gensalt()).decode("utf-8")
    db_user = User(
        username=username.strip(),
        password_hash=hashed,
        totp_secret=pyotp.random_base32(),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def reset_user_password(db: Session, user: User, new_password: str) -> User:
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


app = FastAPI(title="Controle Financeiro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserCreate(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    totp_secret: str
    totp_uri: str


class LoginStep1Request(BaseModel):
    username: str
    password: str


class LoginStep2Request(BaseModel):
    username: str
    code: str


class ResetPasswordRequest(BaseModel):
    username: str
    code: str
    new_password: str


@app.post("/api/auth/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_username(db, user_in.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nome de usuário já cadastrado.")

    try:
        quota = int(os.getenv("ACCOUNT_QUOTA", "0"))
    except Exception:
        quota = 0
    if quota > 0 and count_users(db) >= quota:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Limite de contas atingido.")

    user = create_user(db, user_in.username, user_in.password)
    totp = pyotp.TOTP(user.totp_secret)
    totp_uri = totp.provisioning_uri(name=user.username, issuer_name="ControleFinanceiro")
    return UserResponse(
        id=user.id,
        username=user.username,
        totp_secret=user.totp_secret,
        totp_uri=totp_uri,
    )


@app.post("/api/auth/login/step1")
def login_step1(auth_req: LoginStep1Request, db: Session = Depends(get_db)):
    user = get_user_by_username(db, auth_req.username)
    if not user or not verify_password(auth_req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha incorretos.")
    return {"success": True, "message": "Senha válida. Prossiga para a autenticação em duas etapas."}


@app.post("/api/auth/login/step2")
def login_step2(auth_req: LoginStep2Request, response: Response, db: Session = Depends(get_db)):
    user = get_user_by_username(db, auth_req.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(auth_req.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código de autenticação inválido.")

    session_token = criar_sessao(user.username)
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7200,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return {"success": True, "message": "Autenticado com sucesso.", "session_token": session_token}


@app.post("/api/auth/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = get_user_by_username(db, req.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário não encontrado.")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(req.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código de autenticação inválido para redefinição.")

    reset_user_password(db, user, req.new_password)
    return {"success": True, "message": "Senha redefinida com sucesso."}


@app.post("/api/auth/logout")
def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    encerrar_sessao(session_token)
    response.delete_cookie("session_token", path="/")
    return {"message": "Sessão encerrada."}


@app.post("/api/auth/login/google")
def login_google(payload: dict, response: Response, db: Session = Depends(get_db)):
    id_token = payload.get("id_token")
    if not id_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="id_token ausente")

    try:
        r = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=5,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Google inválido")
        info = r.json()
        email = info.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Google inválido: sem email")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao validar token Google: {str(e)}")

    user = get_user_by_username(db, email)
    if not user:
        try:
            quota = int(os.getenv("ACCOUNT_QUOTA", "0"))
        except Exception:
            quota = 0
        if quota > 0 and count_users(db) >= quota:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Limite de contas atingido.")
        user = create_user_google(db, email)

    session_token = criar_sessao(user.username)
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7200,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return {"success": True, "message": "Autenticado via Google.", "session_token": session_token}


app.include_router(transactions.router)
app.include_router(investments.router)

app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
