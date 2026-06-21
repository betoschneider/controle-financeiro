from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from typing import List, Optional

def get_transacoes_por_ano(db: Session, ano: int) -> List[models.Transacao]:
    """Retorna todas as transações de um ano específico."""
    return db.query(models.Transacao).filter(models.Transacao.ano == ano).all()

def bulk_save_transacoes_por_ano(
    db: Session, ano: int, transacoes_in: List[schemas.TransacaoCreate]
) -> List[models.Transacao]:
    """Deleta todas as transações do ano fornecido e insere a nova lista."""
    # 1. Remove transações antigas para aquele ano
    db.query(models.Transacao).filter(models.Transacao.ano == ano).delete()
    
    # 2. Insere as novas transações
    novas_transacoes = []
    for tx in transacoes_in:
        # Só insere se pelo menos um dos campos (item, tipo, categoria) estiver preenchido
        if tx.item.strip() or tx.tipo.strip() or tx.categoria.strip():
            db_tx = models.Transacao(
                ano=ano,
                mes=tx.mes,
                item=tx.item.strip(),
                tipo=tx.tipo.strip(),
                categoria=tx.categoria.strip(),
                valor=tx.valor,
                pago=tx.pago
            )
            novas_transacoes.append(db_tx)
            
    db.add_all(novas_transacoes)
    db.commit()
    return novas_transacoes

def get_ano_mais_recente(db: Session) -> Optional[int]:
    """Retorna o ano mais recente que possui registros no banco de dados."""
    resultado = db.query(func.max(models.Transacao.ano)).scalar()
    return resultado

def get_dados_molde_ano_mais_recente(db: Session) -> List[models.Transacao]:
    """Busca transações do ano mais recente cadastrado para servir de molde para anos futuros."""
    ano_recente = get_ano_mais_recente(db)
    if not ano_recente:
        return []
    return db.query(models.Transacao).filter(models.Transacao.ano == ano_recente).all()

# --- OPERAÇÕES DE USUÁRIO (AUTENTICAÇÃO & 2FA) ---
import bcrypt
import pyotp

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    hashed = hash_password(user_in.password)
    totp_secret = pyotp.random_base32()
    db_user = models.User(
        username=user_in.username.strip(),
        password_hash=hashed,
        totp_secret=totp_secret
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def reset_user_password(db: Session, user: models.User, new_password: str) -> models.User:
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user

