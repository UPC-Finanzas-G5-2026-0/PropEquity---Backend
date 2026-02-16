from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserRole(str, Enum):
    ADMIN = "administrador"
    ASESOR = "asesor"
    CLIENTE = "cliente"


class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    

class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.ASESOR


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None