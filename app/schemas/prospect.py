from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from decimal import Decimal

class ProspectBase(BaseModel):
    nombres: str = Field(..., max_length=50)
    apellidos: Optional[str] = Field(None, max_length=50)
    telefono: str = Field(..., max_length=20)
    email: Optional[EmailStr] = None
    ingreso_mensual: Decimal = Field(default=0.00, ge=0)
    codigo_asesor: int

class ProspectCreate(ProspectBase):
    pass

class ProspectResponse(ProspectBase):
    codigo_prospecto: int
    fecha_registro: datetime

    class Config:
        from_attributes = True
