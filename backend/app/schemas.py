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

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    totp_secret: str
    totp_uri: str

    class Config:
        from_attributes = True

class LoginStep1Request(BaseModel):
    username: str
    password: str

class LoginStep1Response(BaseModel):
    success: bool
    message: str

class LoginStep2Request(BaseModel):
    username: str
    code: str

class ResetPasswordRequest(BaseModel):
    username: str
    code: str
    new_password: str


class InvestmentPurchase(BaseModel):
    ticker: str
    quantity: int


class InvestmentContributionRequest(BaseModel):
    purchases: List[InvestmentPurchase]
