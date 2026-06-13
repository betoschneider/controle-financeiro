from sqlalchemy import Column, Integer, String, Float, Boolean
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
