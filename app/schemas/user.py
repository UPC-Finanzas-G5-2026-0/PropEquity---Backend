from typing import Optional  # <--- ¡Faltaba esto!
from pydantic import BaseModel, EmailStr

# Esquema base compartido
class UserBase(BaseModel):
    email: EmailStr

# Para recibir datos al crear usuario (Sign Up)
class UserCreate(UserBase):
    password: str
    role: str = "asesor"

# Para responder datos al cliente (sin password)
class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool

    class Config:
        from_attributes = True

# --- Esquemas para Tokens (JWT) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None