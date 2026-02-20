from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr = Field(..., max_length=100)
    nombres: str = Field(..., max_length=50)
    apellidos: str = Field(..., max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    rol_usuario: str = Field("Cliente", pattern="^(Administrador|Asesor|Cliente)$")
    # Campos dinámicos para subtipos
    dni: Optional[str] = Field(None, pattern=r"^\d{8}$")
    telefono: Optional[str] = Field(None, pattern=r"^\d{9}$")
    ingreso_mensual: Optional[float] = Field(None, ge=0)

class UserResponse(UserBase):
    codigo_usuario: int
    codigo_rol: int
    fecha_registro: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    nombres: str
    apellidos: str
    codigo_usuario: int

class TokenData(BaseModel):
    email: Optional[str] = None