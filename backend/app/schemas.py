from pydantic import BaseModel
from typing import List, Optional

class TransacaoBase(BaseModel):
    item: str
    tipo: str
    categoria: str
    valor: float
    pago: bool

class TransacaoCreate(TransacaoBase):
    ano: int
    mes: int

class TransacaoResponse(TransacaoCreate):
    id: int

    class Config:
        from_attributes = True

class AuthRequest(BaseModel):
    token: str

class AuthResponse(BaseModel):
    success: bool
    message: str
