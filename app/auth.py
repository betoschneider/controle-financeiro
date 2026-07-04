import secrets
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, status

ACTIVE_SESSIONS = {}


def verificar_autenticacao(
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None),
) -> str:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif session_token:
        token = session_token

    if not token or token not in ACTIVE_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido ou ausente.",
        )
    return ACTIVE_SESSIONS[token]


def criar_sessao(username: str) -> str:
    session_token = secrets.token_hex(32)
    ACTIVE_SESSIONS[session_token] = username
    return session_token


def encerrar_sessao(session_token: Optional[str]) -> None:
    if session_token and session_token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_token]
