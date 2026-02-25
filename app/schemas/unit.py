from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class UnitBase(BaseModel):
    direccion_unidad: str = Field(..., max_length=70)
    distrito_unidad: str = Field(..., max_length=40)
    area_unidad: float = Field(..., gt=0)
    precio_venta: float = Field(..., ge=68800.00, le=488800.00) # Rango DS 004-2025-VIVIENDA
    codigo_moneda: int = Field(1, ge=1) # 1: PEN, 2: USD
    codigo_modalidad: int = Field(1, ge=1) # 1: Compra, 2: Construccion, 3: Mejoramiento
    codigo_tipo_venta: Optional[int] = Field(1, ge=1) # 1: Primera, 2: Segunda
    es_sostenible: bool = Field(default=False)
    codigo_estado: int = Field(1, ge=1) # 1: Activo, 2: Inactivo
    codigo_cliente: Optional[int] = None 
    codigo_prospecto: Optional[int] = None
    codigo_asesor: Optional[int] = None

class UnitCreate(UnitBase):
    pass

class UnitUpdate(BaseModel):
    direccion_unidad: Optional[str] = Field(None, max_length=70)
    distrito_unidad: Optional[str] = Field(None, max_length=40)
    area_unidad: Optional[float] = Field(None, gt=0)
    precio_venta: Optional[float] = Field(None, ge=68800.00, le=488800.00)
    codigo_moneda: Optional[int] = Field(None, ge=1)
    codigo_modalidad: Optional[int] = None
    codigo_tipo_venta: Optional[int] = None
    es_sostenible: Optional[bool] = None
    codigo_estado: Optional[int] = Field(None, ge=1)
    codigo_cliente: Optional[int] = None
    codigo_prospecto: Optional[int] = None
    codigo_asesor: Optional[int] = None
    foto: Optional[str] = None

class UnitResponse(BaseModel):
    codigo_unidad: int
    direccion_unidad: str
    distrito_unidad: str
    area_unidad: float
    precio_venta: float
    codigo_moneda: int
    codigo_modalidad: int
    codigo_tipo_venta: Optional[int]
    es_sostenible: bool
    codigo_estado: int
    fecha_registro: date
    codigo_cliente: Optional[int] = None
    codigo_prospecto: Optional[int] = None
    codigo_asesor: Optional[int] = None
    foto: Optional[str] = None

    class Config:
        from_attributes = True
