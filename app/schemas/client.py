from pydantic import BaseModel, Field
from typing import Optional

class ClientBase(BaseModel):
    dni_cliente: str = Field(..., pattern=r"^\d{8}$")
    telefono_cliente: str = Field(..., pattern=r"^\d{9}$")
    ingreso_mensual: float = Field(default=0.00, ge=0)

class ClientCreate(ClientBase):
  
    nombres: str
    apellidos: str
    email: str 
class ClientUpdate(BaseModel):
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    dni_cliente: Optional[str] = Field(None, pattern=r"^\d{8}$")
    telefono_cliente: Optional[str] = Field(None, pattern=r"^\d{9}$")
    ingreso_mensual: Optional[float] = Field(None, ge=0)

class ClientResponse(ClientBase):
    codigo_cliente: int
    
    class Config:
        from_attributes = True