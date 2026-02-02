from pydantic import BaseModel, Field
from typing import Optional, List

class SimulationInput(BaseModel):
    precio_venta: float = Field(..., gt=0)
    cuota_inicial: float = Field(..., ge=0)
    tea: float = Field(..., gt=0) # Tasa Efectiva Anual
    plazo_meses: int = Field(..., ge=48, le=300) # [cite: 17]
    tipo_gracia: str = Field("NINGUNO", pattern="^(NINGUNO|PARCIAL|TOTAL)$")
    meses_gracia: int = Field(0, ge=0, le=6)

class PaymentDetail(BaseModel):
    mes: int
    cuota: float
    interes: float
    amortizacion: float
    saldo: float

class SimulationResult(BaseModel):
    cronograma: List[PaymentDetail]
    van: float
    tir: float