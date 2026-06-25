from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from .database import Base

class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    ano = Column(Integer, index=True, nullable=False)
    mes = Column(Integer, index=True, nullable=False)  # 1 a 12
    item = Column(String, index=True, nullable=False)
    tipo = Column(String, index=True, nullable=False)       # Receita, Despesa, Investimento, Reserva, etc.
    categoria = Column(String, index=True, nullable=False)
    valor = Column(Float, nullable=False, default=0.0)
    pago = Column(Boolean, nullable=False, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    totp_secret = Column(String, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    detail = Column(String, nullable=True)


class InvestmentAsset(Base):
    __tablename__ = "investment_assets"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    target = Column(Float, nullable=True)
    sector = Column(String, nullable=True)
    group = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)


