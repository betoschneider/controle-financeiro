from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import verificar_autenticacao
from app.config import get_db
from app.models import (
    Categoria,
    FinancialInsight,
    InvestmentAsset,
    InvestmentInsight,
    InvestmentTransaction,
    Tipo,
    Transacao,
    User,
)
from app.transactions import get_user_by_username

router = APIRouter(prefix="/api/profile", tags=["Perfil"])


def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


class UserProfileResponse(BaseModel):
    username: str
    name: Optional[str] = None
    email: Optional[str] = None
    ai_provider: Optional[str] = None
    api_key: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateAiConfigRequest(BaseModel):
    ai_provider: Optional[str] = None
    api_key: Optional[str] = None


def _get_user(db: Session, username: str) -> User:
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return user


@router.get("", response_model=UserProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Retorna os dados do perfil do usuário logado."""
    user = _get_user(db, username)
    return UserProfileResponse(
        username=user.username,
        name=user.name,
        email=user.email,
        ai_provider=user.ai_provider,
        api_key=user.api_key,
    )


@router.put("", response_model=UserProfileResponse)
def update_profile(
    req: UpdateProfileRequest,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Atualiza nome e email do usuário."""
    user = _get_user(db, username)
    if req.name is not None:
        user.name = req.name.strip() if req.name.strip() else None
    if req.email is not None:
        user.email = req.email.strip() if req.email.strip() else None
    db.commit()
    db.refresh(user)
    return UserProfileResponse(
        username=user.username,
        name=user.name,
        email=user.email,
        ai_provider=user.ai_provider,
        api_key=user.api_key,
    )


@router.put("/password")
def update_password(
    req: UpdatePasswordRequest,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Altera a senha do usuário."""
    user = _get_user(db, username)

    # Verifica senha atual
    if not bcrypt.checkpw(req.current_password.encode("utf-8"), user.password_hash.encode("utf-8")):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter no mínimo 6 caracteres.")

    user.password_hash = _hash_password(req.new_password)
    db.commit()
    return {"success": True, "message": "Senha atualizada com sucesso."}


@router.put("/ai-config", response_model=UserProfileResponse)
def update_ai_config(
    req: UpdateAiConfigRequest,
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Atualiza provedor de IA e chave de API."""
    valid_providers = ["openai", "anthropic", "gemini", "deepseek", None]
    provider = req.ai_provider.lower().strip() if req.ai_provider else None

    if provider and provider not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Provedor inválido. Use: {', '.join(v for v in valid_providers if v)}",
        )

    user = _get_user(db, username)
    user.ai_provider = provider
    user.api_key = req.api_key.strip() if req.api_key else None
    db.commit()
    db.refresh(user)
    return UserProfileResponse(
        username=user.username,
        name=user.name,
        email=user.email,
        ai_provider=user.ai_provider,
        api_key=user.api_key,
    )


@router.delete("")
def delete_account(
    db: Session = Depends(get_db),
    username: str = Depends(verificar_autenticacao),
):
    """Exclui permanentemente a conta do usuário e todos os seus dados."""
    user = _get_user(db, username)

    # Remove dados do usuário em ordem (filhos -> pai)
    db.query(FinancialInsight).filter(FinancialInsight.owner_id == user.id).delete()
    db.query(InvestmentInsight).filter(InvestmentInsight.owner_id == user.id).delete()
    db.query(InvestmentTransaction).filter(InvestmentTransaction.owner_id == user.id).delete()
    db.query(InvestmentAsset).filter(InvestmentAsset.owner_id == user.id).delete()
    db.query(Transacao).filter(Transacao.owner_id == user.id).delete()
    db.query(Categoria).filter(Categoria.owner_id == user.id).delete()
    # Tipos são compartilhados entre usuários, não excluímos
    db.delete(user)
    db.commit()

    return {"success": True, "message": "Conta excluída permanentemente."}
