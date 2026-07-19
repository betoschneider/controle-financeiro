from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from app.config import Base


class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    ano = Column(Integer, index=True, nullable=False)
    mes = Column(Integer, index=True, nullable=False)
    item = Column(String(100), index=True, nullable=False)
    tipo = Column(String(50), index=True, nullable=False)
    categoria = Column(String(50), index=True, nullable=False)
    valor = Column(Float, nullable=False, default=0.0)
    pago = Column(Boolean, nullable=False, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    totp_secret = Column(String, nullable=False)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    ai_provider = Column(String, nullable=True)
    api_key = Column(String, nullable=True)


class InvestmentAsset(Base):
    __tablename__ = "investment_assets"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    purchase_price = Column(Float, nullable=True)
    target = Column(Float, nullable=True)
    sector = Column(String, nullable=True)
    group = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)


class Tipo(Base):
    """Tipos de categoria (ex: Receita, Despesa, etc.)"""
    __tablename__ = "tipos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), unique=True, nullable=False, index=True)
    is_protegido = Column(Boolean, nullable=False, default=False)


class InvestmentTransaction(Base):
    __tablename__ = "investment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    purchase_price = Column(Float, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)


class FinancialInsight(Base):
    __tablename__ = "financial_insights"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)


class InvestmentInsight(Base):
    __tablename__ = "investment_insights"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)


class Categoria(Base):
    """Categorias financeiras vinculadas a tipos e usuários"""
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, index=True)
    valor = Column(Float, nullable=False, default=0.0)
    tipo_id = Column(Integer, ForeignKey("tipos.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    is_protegido = Column(Boolean, nullable=False, default=False)
