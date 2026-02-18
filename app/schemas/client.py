from pydantic import BaseModel, Field
from typing import Optional

class ClientBase(BaseModel):
    dni_cliente: str = Field(..., pattern=r"^\d{8}$")
    telefono_cliente: str = Field(..., pattern=r"^\d{9}$")
    ingreso_mensual: float = Field(default=0.00, ge=0)

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    codigo_cliente: int
    class Config:
        from_attributes = True