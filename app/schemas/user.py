from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico institucional o personal")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Contraseña de acceso (mínimo 8 caracteres)")

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool = True

    class Config:
        from_attributes = True

# Esquemas para el Token JWT
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None