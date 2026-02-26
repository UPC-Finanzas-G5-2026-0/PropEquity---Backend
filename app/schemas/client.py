from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

# --- Schemas embebidos para evitar referencias circulares ---

class UnitSummary(BaseModel):
    codigo_unidad: int
    direccion_unidad: str
    distrito_unidad: str
    area_unidad: float
    precio_venta: float
    codigo_estado: int
    codigo_modalidad: int
    foto: Optional[str] = None

    class Config:
        from_attributes = True

class SimulationSummary(BaseModel):
    codigo_simulacion: int
    fecha_simulacion: date
    plazo_meses: int
    tasa_anual: Decimal
    codigo_unidad: int
    bono_bbp: Decimal

    class Config:
        from_attributes = True

# --- Schemas principales ---

class ClientBase(BaseModel):
    dni_cliente: str = Field(..., pattern=r"^\d{8}$")
    telefono_cliente: str = Field(..., pattern=r"^9\d{8}$")
    ingreso_mensual: float = Field(default=0.00, ge=0)
    codigo_tipo_ingreso: int = Field(default=1)
    meses_ahorro: int = Field(default=0, ge=0)
    tiene_deudor_solidario: bool = Field(default=False)
    residencia: str = Field(default="Peruano")
    codigo_estado_civil: Optional[int] = None
    nombre_conyuge: Optional[str] = None
    doc_conyuge: Optional[str] = None
    conyuge_propietario: bool = Field(default=False)
    es_propietario_vivienda: bool = Field(default=False)

    @model_validator(mode='after')
    def validate_client_rules(self) -> 'ClientBase':
        # Regla Ahorro Programado
        if self.codigo_tipo_ingreso == 3 and self.meses_ahorro < 6:
            raise ValueError("Mínimo 6 meses de ahorro para ahorro programado.")
        # Regla Cónyuge
        if self.codigo_estado_civil in [2, 3]:
            if not self.nombre_conyuge or not self.doc_conyuge:
                raise ValueError("Nombre y Doc del cónyuge obligatorios para Casado/Conviviente.")
        return self

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    dni_cliente: Optional[str] = Field(None, pattern=r"^\d{8}$")
    telefono_cliente: Optional[str] = Field(None, pattern=r"^9\d{8}$")
    ingreso_mensual: Optional[float] = Field(None, ge=0)
    codigo_tipo_ingreso: Optional[int] = None
    meses_ahorro: Optional[int] = None
    tiene_deudor_solidario: Optional[bool] = None
    residencia: Optional[str] = None
    codigo_estado_civil: Optional[int] = None
    nombre_conyuge: Optional[str] = None
    doc_conyuge: Optional[str] = None
    conyuge_propietario: Optional[bool] = None
    es_propietario_vivienda: Optional[bool] = None
    nombres: Optional[str] = Field(None, max_length=50)
    apellidos: Optional[str] = Field(None, max_length=50)

from app.schemas.user import UserResponse

class ClientResponse(BaseModel):
    """Schema de respuesta completo con unidades y simulaciones asociadas."""
    codigo_cliente: int
    dni_cliente: Optional[str] = None
    telefono_cliente: Optional[str] = None
    ingreso_mensual: Optional[float] = None
    codigo_tipo_ingreso: Optional[int] = None
    meses_ahorro: Optional[int] = None
    tiene_deudor_solidario: Optional[bool] = None
    residencia: Optional[str] = None
    codigo_estado_civil: Optional[int] = None
    nombre_conyuge: Optional[str] = None
    doc_conyuge: Optional[str] = None
    conyuge_propietario: Optional[bool] = None
    es_propietario_vivienda: Optional[bool] = None
    usuario: UserResponse
    # Relaciones embebidas
    unidades: List[UnitSummary] = []
    simulaciones: List[SimulationSummary] = []

    class Config:
        from_attributes = True
