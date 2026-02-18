from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class UnitBase(BaseModel):
    direccion_unidad: str = Field(..., max_length=70)
    distrito_unidad: str = Field(..., max_length=40)
    area_unidad: float = Field(..., gt=0)
    precio_venta: float = Field(..., gt=0)
    codigo_moneda: int = Field(1, ge=1) # 1: PEN, 2: USD
    codigo_estado: int = Field(1, ge=1) # 1: Activo, 2: Inactivo
    codigo_cliente: Optional[int] = None 
    codigo_prospecto: Optional[int] = None
    codigo_asesor: Optional[int] = None

class UnitCreate(UnitBase):
    pass

class UnitResponse(BaseModel):
    codigo_unidad: int
    direccion_unidad: str
    distrito_unidad: str
    area_unidad: float
    precio_venta: float
    codigo_moneda: int
    codigo_estado: int
    fecha_registro: date
    codigo_cliente: Optional[int] = None
    codigo_prospecto: Optional[int] = None
    codigo_asesor: Optional[int] = None
    foto: Optional[str] = None

    class Config:
        from_attributes = True
