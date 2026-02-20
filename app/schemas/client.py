from pydantic import BaseModel, Field
from typing import Optional

class ClientBase(BaseModel):
    dni_cliente: str = Field(..., pattern=r"^\d{8}$")
    telefono_cliente: str = Field(..., pattern=r"^\d{9}$")
    ingreso_mensual: float = Field(default=0.00, ge=0)

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    dni_cliente: Optional[str] = Field(None, pattern=r"^\d{8}$")
    telefono_cliente: Optional[str] = Field(None, pattern=r"^\d{9}$")
    ingreso_mensual: Optional[float] = Field(None, ge=0)
    nombres: Optional[str] = Field(None, max_length=50)
    apellidos: Optional[str] = Field(None, max_length=50)

from app.schemas.user import UserResponse

class ClientResponse(ClientBase):
    codigo_cliente: int
    usuario: UserResponse

    class Config:
        from_attributes = True