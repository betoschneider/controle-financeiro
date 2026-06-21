from pydantic import BaseModel, EmailStr
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
    username: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: EmailStr
    totp_secret: str
    totp_uri: str

    class Config:
        from_attributes = True

class LoginStep1Request(BaseModel):
    username: EmailStr
    password: str

class LoginStep1Response(BaseModel):
    success: bool
    message: str

class LoginStep2Request(BaseModel):
    username: EmailStr
    code: str

class ResetPasswordRequest(BaseModel):
    username: EmailStr
    code: str
    new_password: str


