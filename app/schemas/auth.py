import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CadastroRequest(BaseModel):
    matricula: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)


class LoginRequest(BaseModel):
    matricula: str = Field(min_length=1, max_length=50)
    password: str


class UsuarioPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    matricula: str
    email: EmailStr
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioPublic
