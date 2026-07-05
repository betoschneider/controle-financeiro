from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String

from app.config import Base


class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    ano = Column(Integer, index=True, nullable=False)
    mes = Column(Integer, index=True, nullable=False)
    item = Column(String(100), index=True, nullable=False)  # Limite de comprimento
    tipo = Column(String(50), index=True, nullable=False)  # Limite de comprimento
    categoria = Column(String(50), index=True, nullable=False)  # Limite de comprimento
    valor = Column(Float, nullable=False, default=0.0)
    pago = Column(Boolean, nullable=False, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    totp_secret = Column(String, nullable=False)


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
