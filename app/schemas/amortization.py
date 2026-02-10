from pydantic import BaseModel, Field
from typing import List, Optional


class FrenchScheduleInput(BaseModel):
    principal: float = Field(..., gt=0)
    rate: float = Field(..., ge=0)
    rate_type: str = Field(..., min_length=1)
    n_periods: int = Field(..., gt=0)
    payment_period: str = Field("monthly")
    capitalization: Optional[str] = Field(None)
    rate_period: Optional[str] = Field(None)


class FrenchPaymentDetail(BaseModel):
    periodo: int
    saldo_inicial: float
    cuota: float
    interes: float
    amortizacion: float
    saldo_final: float


class FrenchScheduleResult(BaseModel):
    cronograma: List[FrenchPaymentDetail]
