from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from enum import Enum

# --- 1. ENUMS ---
class TipoTasa(str, Enum):
    NOMINAL = "TNA"
    EFECTIVA = "TEA"

class FrecuenciaCapitalizacion(str, Enum):
    DIARIA = "diaria"
    MENSUAL = "mensual"
    SEMESTRAL = "semestral"

class TipoGracia(str, Enum):
    NINGUNO = "sin_gracia"
    PARCIAL = "parcial"
    TOTAL = "total"

class Moneda(str, Enum):
    PEN = "PEN"
    USD = "USD"

# --- 2. INPUT ---
class SimulationInput(BaseModel):
    moneda: Moneda = Moneda.PEN
    precio_venta: float = Field(..., gt=0, description="Precio del inmueble")
    cuota_inicial: float = Field(..., gt=0, description="Monto del pago inicial")
    bono_bbp: float = Field(default=0.0, ge=0, description="Bono del Buen Pagador")

    tipo_tasa: TipoTasa = TipoTasa.EFECTIVA
    tasa_valor: float = Field(..., gt=0, description="Valor porcentual de la tasa")
    capitalization: Optional[FrecuenciaCapitalizacion] = None
    
    plazo_meses: int = Field(..., ge=48, le=300, description="Plazo en meses")
    
    seguro_desgravamen_porc: float = Field(..., ge=0, description="% Mensual desgravamen")
    seguro_inmueble_anual: float = Field(..., ge=0, description="% Anual inmueble")

    tipo_gracia: TipoGracia = TipoGracia.NINGUNO
    meses_gracia: int = Field(0, ge=0, le=6, description="Meses de gracia")

    @model_validator(mode='after')
    def validar_reglas_negocio(self):
        if self.cuota_inicial >= self.precio_venta:
            raise ValueError("La cuota inicial no puede ser mayor al precio.")
        if self.tipo_tasa == TipoTasa.NOMINAL and not self.capitalization:
            raise ValueError("TNA requiere frecuencia de capitalización.")
        if self.tipo_gracia != TipoGracia.NINGUNO and self.meses_gracia <= 0:
            raise ValueError("Indique meses de gracia válidos.")
        return self

# --- 3. OUTPUT ---
class PaymentDetail(BaseModel):
    numero_cuota: int
    saldo_inicial: float
    amortizacion: float
    interes: float
    seguro_desgravamen: float
    seguro_inmueble: float
    cuota_total: float
    saldo_final: float
    flujo_caja: float

class SimulationResult(BaseModel):
    input_resumen: dict
    cronograma: List[PaymentDetail]
    indicadores: dict