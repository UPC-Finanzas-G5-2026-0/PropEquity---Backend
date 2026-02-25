from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal

class ProspectBase(BaseModel):
    nombres: str = Field(..., max_length=50)
    apellidos: Optional[str] = Field(None, max_length=50)
    telefono: str = Field(..., pattern=r"^9\d{8}$")
    email: Optional[EmailStr] = None
    ingreso_mensual: Decimal = Field(default=0.00, ge=0)
    codigo_tipo_ingreso: int = Field(default=1)
    meses_ahorro: int = Field(default=0, ge=0)
    tiene_deudor_solidario: bool = Field(default=False)
    residencia: str = Field(default="Peruano")
    codigo_estado_civil: Optional[int] = None
    nombre_conyuge: Optional[str] = None
    doc_conyuge: Optional[str] = None
    conyuge_propietario: bool = Field(default=False)
    es_propietario_vivienda: bool = Field(default=False)
    codigo_asesor: int

    @model_validator(mode='after')
    def validate_prospect_rules(self) -> 'ProspectBase':
        # Regla Ahorro Programado
        if self.codigo_tipo_ingreso == 3 and self.meses_ahorro < 6:
            raise ValueError("Mínimo 6 meses de ahorro para ahorro programado.")
        
        # Regla Cónyuge
        if self.codigo_estado_civil in [2, 3]:
            if not self.nombre_conyuge or not self.doc_conyuge:
                raise ValueError("Nombre y Doc del cónyuge obligatorios para Casado/Conviviente.")
        return self

class ProspectCreate(ProspectBase):
    pass

class ProspectUpdate(BaseModel):
    """Todos los campos opcionales para actualizaciones parciales."""
    nombres: Optional[str] = Field(None, max_length=50)
    apellidos: Optional[str] = Field(None, max_length=50)
    telefono: Optional[str] = Field(None, pattern=r"^9\d{8}$")
    email: Optional[EmailStr] = None
    ingreso_mensual: Optional[Decimal] = Field(None, ge=0)
    codigo_tipo_ingreso: Optional[int] = None
    meses_ahorro: Optional[int] = Field(None, ge=0)
    tiene_deudor_solidario: Optional[bool] = None
    residencia: Optional[str] = None
    codigo_estado_civil: Optional[int] = None
    nombre_conyuge: Optional[str] = None
    doc_conyuge: Optional[str] = None
    conyuge_propietario: Optional[bool] = None
    es_propietario_vivienda: Optional[bool] = None


class ProspectResponse(ProspectBase):
    codigo_prospecto: int
    fecha_registro: datetime

    class Config:
        from_attributes = True
