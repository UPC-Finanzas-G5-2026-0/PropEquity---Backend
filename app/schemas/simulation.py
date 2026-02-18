from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import date
from decimal import Decimal

class SimulationBase(BaseModel):
    cuota_inicial: Decimal = Field(default=0.00, ge=0)
    bono_bbp: Decimal = Field(default=0.00, ge=0)
    tasa_anual: Decimal = Field(..., gt=0)
    capitalizacion: str = Field("Mensual")
    plazo_meses: int = Field(..., ge=48, le=300)
    codigo_tipo_gracia: int = Field(1, ge=1) # 1: Ninguno, 2: Parcial, 3: Total
    meses_gracia: int = Field(0, ge=0)
    seguro_desgravamen: Decimal = Field(default=0.00, ge=0)
    codigo_tipo_tasa: int = Field(2, ge=1) # 1: Nominal, 2: Efectiva
    codigo_unidad: int
    codigo_cliente: Optional[int] = None
    codigo_prospecto: Optional[int] = None
    codigo_asesor: Optional[int] = None

class SimulationCreate(SimulationBase):
    pass

class SimulationSummaryResponse(BaseModel):
    # Intermedios
    precio_neto: Decimal
    monto_financiar: Decimal
    tasa_periodica: Decimal
    tasa_efectiva_mensual: Decimal
    factor_frances: Decimal

    # Salidas (Outputs)
    van: Decimal
    tir: Decimal
    tcea: Decimal
    total_intereses: Decimal
    total_pagado: Decimal
    total_seguro: Decimal

    class Config:
        from_attributes = True

class SimulationDetailResponse(BaseModel):
    numero_cuota: int
    cuota_total: Decimal
    interes: Decimal
    amortizacion: Decimal
    seguro: Decimal
    saldo_final: Decimal

    class Config:
        from_attributes = True

class SimulationResponse(SimulationBase):
    codigo_simulacion: int
    fecha_simulacion: date
    
    # Datos relacionados de las tablas hermanas
    resumen: Optional[SimulationSummaryResponse] = None
    detalles: List[SimulationDetailResponse] = []

    class Config:
        from_attributes = True

class SimulationResult(BaseModel):
    codigo_simulacion: int
    codigo_unidad: int
    cronograma: List[SimulationDetailResponse]
    van: float
    tir: float
