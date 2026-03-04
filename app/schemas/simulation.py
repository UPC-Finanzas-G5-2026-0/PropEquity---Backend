from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Literal
from datetime import date
from decimal import Decimal
from app.schemas.unit import UnitResponse

TIPOS_BBP = ["Ninguno", "Tradicional", "Sostenible", "Integrador Tradicional", "Integrador Sostenible"]
CATEGORIAS_INTEGRADOR = ["Menores ingresos", "Adulto mayor", "Discapacidad", "Desplazado", "Migrante retornado"]
IFIS = ["BCP", "BBVA", "Interbank", "Pichincha", "GNB"]

class SimulationBase(BaseModel):
    # Cuota inicial y gastos — validación cruzada con precio_venta en el endpoint
    cuota_inicial: float = Field(default=0.00, ge=0)
    coste_notarial: float = Field(default=0.00, ge=0)
    coste_registral: float = Field(default=0.00, ge=0)
    tasacion: float = Field(default=0.00, ge=0)
    comision_estudio: float = Field(default=0.00, ge=0)
    comision_activacion: float = Field(default=0.00, ge=0)
    
    gastos_iniciales: float = Field(default=0.00, ge=0)
    # Total de gastos (notaría, registros, tasación, comisiones)

    # Gastos periódicos (Mensuales)
    comision_periodica: float = Field(default=0.00, ge=0)
    portes: float = Field(default=0.00, ge=0)
    gastos_administracion: float = Field(default=0.00, ge=0)

    # BBP
    tipo_bbp: str = Field(default="Ninguno")
    categoria_integrador: Optional[str] = None
    ingreso_maximo_integrador: Optional[float] = Field(None, ge=0)
    tiene_deudor_solidario: bool = Field(default=False)

    # IFI (opcional)
    ifi_seleccionada: Optional[str] = None

    # Tasa y Moneda
    tipo_tasa: str = Field(default="Efectiva")      # "Nominal" / "Efectiva"
    tasa_anual: float = Field(..., gt=0)  # Cambiar de Decimal a float para evitar serialización
    capitalizacion: str = Field(default="Mensual")  # Solo si tipo_tasa = "Nominal"
    tipo_cambio: float = Field(default=3.75, ge=2.0, le=5.0)  # Cambiar de Decimal a float

    # Plazo
    plazo_meses: int = Field(...)

    # Gracia
    tipo_gracia: str = Field(default="Ninguno")     # "Ninguno" / "Parcial" / "Total"
    meses_gracia: int = Field(default=0, ge=0, le=6, description="Máximo 6 meses de gracia")

    # Seguro (tasa sobre saldo)
    seguro_desgravamen: float = Field(default=0.000000, ge=0)

    # Relaciones
    codigo_unidad: int
    codigo_cliente: Optional[int] = None
    codigo_prospecto: Optional[int] = None
    codigo_asesor: Optional[int] = None

    # Fecha
    fecha_inicio_prestamo: Optional[date] = None

    @field_validator("plazo_meses")
    @classmethod
    def validate_plazo_meses(cls, v):
        if v < 60:
            raise ValueError("El plazo mínimo permitido es de 60 meses (5 años).")
        if v > 240:
            raise ValueError("El plazo máximo permitido es de 240 meses (20 años).")
        return v

    @field_validator("tipo_bbp")
    @classmethod
    def validate_tipo_bbp(cls, v):
        # Simplificar validación para evitar errores de serialización
        # La validación completa se hace en el endpoint
        return v

    @field_validator("tipo_tasa")
    @classmethod
    def validate_tipo_tasa(cls, v):
        if v not in ["Nominal", "Efectiva"]:
            raise ValueError("tipo_tasa debe ser 'Nominal' o 'Efectiva'")
        return v

    @field_validator("tipo_gracia")
    @classmethod
    def validate_tipo_gracia(cls, v):
        if v not in ["Ninguno", "Parcial", "Total"]:
            raise ValueError("tipo_gracia debe ser 'Ninguno', 'Parcial' o 'Total'")
        return v

    @field_validator("capitalizacion")
    @classmethod
    def validate_capitalizacion(cls, v):
        if v not in ["Mensual", "Bimestral", "Trimestral"]:
            raise ValueError("capitalizacion debe ser 'Mensual', 'Bimestral' o 'Trimestral'")
        return v

    @field_validator("ifi_seleccionada")
    @classmethod
    def validate_ifi(cls, v):
        if v is not None and v not in IFIS:
            raise ValueError(f"ifi_seleccionada debe ser una de: {IFIS} o null")
        return v

    @model_validator(mode="after")
    def validate_cross_fields(self) -> "SimulationBase":
        # ─── REGLAS IFI vs MANUAL ─────────────────────────────────────────────
        if self.ifi_seleccionada:
            # Si hay IFI, la tasa SE PRECARGA como Efectiva y se bloquea capitalizacion
            self.tipo_tasa = "Efectiva"
            self.capitalizacion = "Mensual"
        else:
            # Modo manual: si la tasa es Efectiva, la capitalización no aplica
            if self.tipo_tasa == "Efectiva":
                self.capitalizacion = "Mensual"
            # Si es Nominal, el usuario puede elegir la capitalización (que ya validamos)

        # ─── REGLAS BBP INTEGRADOR ─────────────────────────────────────────── 
        # MOVER LAS VALIDACIONES PROBLEMÁTICAS AL ENDPOINT
        # ─── VALIDACIÓN BÁSICA DE PERÍODO DE GRACIA ─────────────────────────────
        # MOVER AL ENDPOINT PARA EVITAR ERRORES DE SERIALIZACIÓN

        return self


class SimulationCreate(SimulationBase):
    pass


class SimulationSummaryResponse(BaseModel):
    rango_bbp: str
    bono_bbp_base: Decimal
    bono_integrador_adicional: Decimal
    precio_neto: Decimal
    monto_financiar: Decimal
    tasa_efectiva_anual: Decimal
    tasa_efectiva_mensual: Decimal
    factor_frances: Decimal
    cuota_base: Decimal
    ratio_cuota_ingreso: Decimal
    van: Decimal
    tir: Decimal
    tcea: Decimal
    tasa_descuento: Decimal
    tasa_descuento_mensual: Optional[Decimal] = Decimal("0.00")
    total_intereses: Decimal
    total_pagado: Decimal
    total_seguro: Decimal
    total_comisiones_periodicas: Optional[Decimal] = Decimal("0.00")
    total_portes_gastos_adm: Optional[Decimal] = Decimal("0.00")


    class Config:
        from_attributes = True

class SimulationDetailResponse(BaseModel):
    numero_cuota: int
    fecha_vencimiento: Optional[date] = None
    fecha_pago: Optional[date] = None # Alias para el frontend
    tea: Optional[Decimal] = None
    tem: Optional[Decimal] = None
    plazo_gracia: Optional[str] = "Sin Gracia"
    saldo_inicio: Optional[Decimal] = None
    saldo_inicial: Optional[Decimal] = None # Alias para el frontend
    interes: Optional[Decimal] = Decimal("0.00")
    interes_capitalizado: Optional[Decimal] = Decimal("0.00")
    amortizacion: Optional[Decimal] = Decimal("0.00")
    seguro: Optional[Decimal] = Decimal("0.00")
    seguro_desgravamen: Optional[Decimal] = None # Alias para el frontend
    comision_periodica: Optional[Decimal] = Decimal("0.00")
    portes: Optional[Decimal] = Decimal("0.00")
    gastos_administracion: Optional[Decimal] = Decimal("0.00")
    cuota_total: Optional[Decimal] = Decimal("0.00")

    cuota: Optional[Decimal] = None # Alias para el frontend
    flujo: Optional[Decimal] = None # Alias para la columna de flujo en frontend
    saldo_final: Optional[Decimal] = Decimal("0.00")
    flujo_caja: Optional[Decimal] = None

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def populate_aliases(self) -> "SimulationDetailResponse":
        if self.flujo is None:
            self.flujo = self.flujo_caja
        if self.cuota is None:
            self.cuota = self.cuota_total
        if self.fecha_pago is None:
            self.fecha_pago = self.fecha_vencimiento
        if self.saldo_inicial is None:
            self.saldo_inicial = self.saldo_inicio
        if self.seguro_desgravamen is None:
            self.seguro_desgravamen = self.seguro
        return self


class SimulationResponse(BaseModel):
    codigo_simulacion: Optional[int] = None
    fecha_simulacion: date
    fecha_inicio_prestamo: date
    cuota_inicial: Decimal
    gastos_iniciales: Decimal
    coste_notarial: Decimal
    coste_registral: Decimal
    tasacion: Decimal
    comision_estudio: Decimal
    comision_activacion: Decimal
    comision_periodica: Optional[Decimal] = Decimal("0.00")
    portes: Optional[Decimal] = Decimal("0.00")
    gastos_administracion: Optional[Decimal] = Decimal("0.00")
    tipo_bbp: str
    bono_bbp: Decimal
    categoria_integrador: Optional[str] = None
    ingreso_maximo_integrador: Optional[Decimal] = None
    ifi_seleccionada: Optional[str] = None
    tipo_tasa: str
    tasa_anual: Decimal
    capitalizacion: str
    plazo_meses: int
    tipo_gracia: str
    meses_gracia: int
    seguro_desgravamen: Decimal
    codigo_unidad: int
    codigo_cliente: Optional[int] = None
    codigo_prospecto: Optional[int] = None
    codigo_asesor: Optional[int] = None
    resumen: Optional[SimulationSummaryResponse] = None
    detalles: List[SimulationDetailResponse] = []
    unidad_rel: Optional[UnitResponse] = None

    # Campos top-level para el frontend
    direccion_unidad: Optional[str] = None
    distrito_unidad: Optional[str] = None
    tea: Optional[Decimal] = None
    tem: Optional[Decimal] = None
    van: Optional[Decimal] = None
    tir: Optional[Decimal] = None
    tcea: Optional[Decimal] = None
    monto_financiamiento: Optional[Decimal] = None
    cuota_mensual: Optional[Decimal] = None

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def populate_flattened_fields(self) -> "SimulationResponse":
        # Rellenar campos de la unidad
        if self.unidad_rel:
            self.direccion_unidad = self.unidad_rel.direccion_unidad
            self.distrito_unidad = self.unidad_rel.distrito_unidad
        
        # Rellenar campos financieros desde el resumen
        if self.resumen:
            self.monto_financiamiento = self.resumen.monto_financiar
            self.cuota_mensual = self.resumen.cuota_base
            self.tea = self.resumen.tasa_efectiva_anual
            self.tem = self.resumen.tasa_efectiva_mensual
            self.van = self.resumen.van
            self.tir = self.resumen.tir
            self.tcea = self.resumen.tcea
            
        return self
