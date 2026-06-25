from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from typing import List, Optional
from datetime import datetime

def get_transacoes_por_ano(db: Session, ano: int, username: Optional[str]) -> List[models.Transacao]:
    """Retorna todas as transações de um ano específico para o usuário fornecido."""
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []
    return db.query(models.Transacao).filter(
        models.Transacao.ano == ano,
        models.Transacao.owner_id == user.id
    ).all()

def bulk_save_transacoes_por_ano(
    db: Session, ano: int, transacoes_in: List[schemas.TransacaoCreate], username: Optional[str]
) -> List[models.Transacao]:
    """Deleta todas as transações do ano fornecido para o usuário e insere a nova lista."""
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []

    # 1. Remove transações antigas para aquele ano e usuário
    db.query(models.Transacao).filter(
        models.Transacao.ano == ano,
        models.Transacao.owner_id == user.id
    ).delete()
    
    # 2. Insere as novas transações atribuídas ao usuário
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
                pago=tx.pago,
                owner_id=user.id
            )
            novas_transacoes.append(db_tx)
            
    db.add_all(novas_transacoes)
    db.commit()
    return novas_transacoes

def get_ano_mais_recente(db: Session, username: Optional[str]) -> Optional[int]:
    """Retorna o ano mais recente que possui registros no banco de dados para o usuário."""
    if not username:
        return None
    user = get_user_by_username(db, username)
    if not user:
        return None
    resultado = db.query(func.max(models.Transacao.ano)).filter(models.Transacao.owner_id == user.id).scalar()
    return resultado

def get_dados_molde_ano_mais_recente(db: Session, username: Optional[str]) -> List[models.Transacao]:
    """Busca transações do ano mais recente cadastrado para servir de molde para anos futuros (por usuário)."""
    ano_recente = get_ano_mais_recente(db, username)
    if not ano_recente:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []
    return db.query(models.Transacao).filter(
        models.Transacao.ano == ano_recente,
        models.Transacao.owner_id == user.id
    ).all()

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


def count_users(db: Session) -> int:
    return db.query(models.User).count()


def create_user_google(db: Session, username: str) -> models.User:
    """Cria um usuário para login via OAuth (gera senha e totp_secret aleatórios)."""
    import pyotp
    import bcrypt
    # Create a random password hash so field is populated (user won't use it)
    random_pw = bcrypt.gensalt()
    hashed = bcrypt.hashpw(random_pw, bcrypt.gensalt()).decode('utf-8')
    totp_secret = pyotp.random_base32()
    db_user = models.User(
        username=username.strip(),
        password_hash=hashed,
        totp_secret=totp_secret
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_audit_log(db: Session, user: Optional[models.User], action: str, detail: Optional[str] = None):
    """Insere um registro de auditoria simples."""
    timestamp = datetime.utcnow().isoformat()
    user_id = user.id if user else None
    log = models.AuditLog(timestamp=timestamp, user_id=user_id, action=action, detail=detail)
    db.add(log)
    db.commit()
    return log


def list_audit_logs(db: Session, username: Optional[str], limit: int = 100) -> List[models.AuditLog]:
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []
    return db.query(models.AuditLog).filter(
        models.AuditLog.user_id == user.id
    ).order_by(models.AuditLog.id.desc()).limit(limit).all()


# --- CRUD para Investimentos ---
def list_investments(db: Session, username: Optional[str]) -> List[models.InvestmentAsset]:
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []
    return db.query(models.InvestmentAsset).filter(models.InvestmentAsset.owner_id == user.id).all()

def delete_all_investments(db: Session, username: Optional[str]):
    if not username:
        return 0
    user = get_user_by_username(db, username)
    if not user:
        return 0
    cnt = db.query(models.InvestmentAsset).filter(models.InvestmentAsset.owner_id == user.id).delete()
    db.commit()
    return cnt

def bulk_create_investments(db: Session, assets: List[dict], username: Optional[str]) -> List[models.InvestmentAsset]:
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []
    created = []
    for a in assets:
        ia = models.InvestmentAsset(
            company=(a.get('company') or '').strip(),
            ticker=(a.get('ticker') or '').strip(),
            quantity=int(a.get('quantity') or 0),
            target=float(a.get('target')) if a.get('target') not in (None, '') else None,
            sector=(a.get('sector') or '').strip(),
            group=(a.get('group') or '').strip(),
            owner_id=user.id
        )
        db.add(ia)
        created.append(ia)
    db.commit()
    return created


def update_investment_quantities(db: Session, username: Optional[str], purchases: List[dict]) -> List[models.InvestmentAsset]:
    if not username:
        return []
    user = get_user_by_username(db, username)
    if not user:
        return []

    updated = []
    for purchase in purchases:
        ticker = (purchase.get("ticker") or "").strip()
        quantity = int(purchase.get("quantity") or 0)
        if not ticker or quantity <= 0:
            continue

        asset = db.query(models.InvestmentAsset).filter(
            models.InvestmentAsset.owner_id == user.id,
            models.InvestmentAsset.ticker == ticker
        ).first()
        if asset:
            asset.quantity = int(asset.quantity or 0) + quantity
            updated.append(asset)

    db.commit()
    for asset in updated:
        db.refresh(asset)
    return updated

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
