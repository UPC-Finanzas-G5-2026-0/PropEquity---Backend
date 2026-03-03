from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Numeric, Date, DateTime, CheckConstraint, CHAR, Boolean
from sqlalchemy.orm import relationship
from .database import Base

class Moneda(Base):
    __tablename__ = "monedas"
    codigo_moneda = Column(Integer, primary_key=True)
    simbolo_moneda = Column(CHAR(3), unique=True, nullable=False) # 'PEN', 'USD'
    tipo_moneda = Column(String(50), nullable=False) # 'Soles', 'Dólares'

    unidades = relationship("Unit", back_populates="moneda_rel")

class EstadoRegistroUnidad(Base):
    __tablename__ = "estados_registro_unidad"
    codigo_estado = Column(Integer, primary_key=True)
    tipo_estado = Column(String(50), unique=True, nullable=False) # 'Activo', 'Inactivo'

    unidades = relationship("Unit", back_populates="estado_rel")

class BonoBBP(Base):
    __tablename__ = "bonos_bbp"
    codigo_bono = Column(Integer, primary_key=True, autoincrement=True)
    rango = Column(String(5), nullable=False) # R1, R2, R3, R4, R5
    valor_vivienda_min = Column(Numeric(12, 2), nullable=False)
    valor_vivienda_max = Column(Numeric(12, 2), nullable=False)
    bono_tradicional = Column(Numeric(12, 2), default=0.00)
    bono_sostenible = Column(Numeric(12, 2), default=0.00)
    bono_integrador_tradicional = Column(Numeric(12, 2), default=0.00)
    bono_integrador_sostenible = Column(Numeric(12, 2), default=0.00)

class CreditoIFI(Base):
    """Tabla de tasas y seguros por IFI, rango de monto y plazo (Créditos MiVivienda 2023)."""
    __tablename__ = "creditos_ifi"
    codigo_credito = Column(Integer, primary_key=True, autoincrement=True)
    nombre_ifi = Column(String(50), nullable=False)          # 'BCP', 'BBVA', 'Interbank', 'Pichincha', 'GNB'
    monto_min = Column(Numeric(12, 2), nullable=False)       # Monto mínimo del crédito
    monto_max = Column(Numeric(12, 2), nullable=True)        # Null = sin límite superior
    plazo_min_anios = Column(Integer, nullable=False)        # Plazo mínimo (años)
    plazo_max_anios = Column(Integer, nullable=False)        # Plazo máximo (años)
    tea_min = Column(Numeric(6, 4), nullable=False)          # TEA mínima (%)
    tea_max = Column(Numeric(6, 4), nullable=False)          # TEA máxima (%)
    seguro_individual = Column(Numeric(6, 4), nullable=False)    # Tasa seguro individual (%)
    seguro_mancomunado = Column(Numeric(6, 4), nullable=False)   # Tasa seguro mancomunado (%)

class RolUsuario(Base):
    __tablename__ = "roles_usuario"
    codigo_rol = Column(Integer, primary_key=True, autoincrement=True)
    tipo_rol = Column(String(50), unique=True, nullable=False) # 'Administrador', 'Asesor', 'Cliente'

    usuarios = relationship("User", back_populates="rol_rel")

class TipoTasa(Base):
    __tablename__ = "tipos_tasa"
    codigo_tipo_tasa = Column(Integer, primary_key=True)
    tipo = Column(String(50), unique=True, nullable=False) # 'Nominal', 'Efectiva'
    # Nota: Simulation ya no referencia esta tabla por FK, usa campo varchar directo

class TipoGracia(Base):
    __tablename__ = "tipos_gracia"
    codigo_tipo_gracia = Column(Integer, primary_key=True)
    tipo = Column(String(50), unique=True, nullable=False) # 'Ninguno', 'Parcial', 'Total'
    # Nota: Simulation ya no referencia esta tabla por FK, usa campo varchar directo

class TipoIngreso(Base):
    __tablename__ = "tipos_ingreso"
    codigo_tipo_ingreso = Column(Integer, primary_key=True)
    nombre_tipo_ingreso = Column(String(30), unique=True, nullable=False) # 'Dependiente', 'Independiente', 'Ahorro programado'

    clientes = relationship("Client", back_populates="tipo_ingreso_rel")

class EstadoCivil(Base):
    __tablename__ = "estados_civil"
    codigo_estado_civil = Column(Integer, primary_key=True)
    nombre_estado_civil = Column(String(20), unique=True, nullable=False) # 'Soltero', 'Casado', 'Conviviente', 'Divorciado', 'Viudo'

    clientes = relationship("Client", back_populates="estado_civil_rel")

class User(Base):
    __tablename__ = "users"
    codigo_usuario = Column(Integer, primary_key=True, autoincrement=True)
    nombres = Column(String(50), nullable=False)
    apellidos = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow, nullable=False)

    codigo_rol = Column(Integer, ForeignKey("roles_usuario.codigo_rol"), nullable=False)
    rol_rel = relationship("RolUsuario", back_populates="usuarios")

    cliente = relationship("Client", back_populates="usuario", uselist=False)
    administrador = relationship("Administrator", back_populates="usuario", uselist=False)
    asesor_rel = relationship("Advisor", back_populates="usuario", uselist=False)

class Administrator(Base):
    __tablename__ = "administrators"
    codigo_administrador = Column(Integer, ForeignKey("users.codigo_usuario"), primary_key=True)
    dni_administrador = Column(CHAR(8), unique=True, nullable=False)
    telefono_administrador = Column(CHAR(9))

    usuario = relationship("User", back_populates="administrador")

class Advisor(Base):
    __tablename__ = "advisors"
    codigo_asesor = Column(Integer, ForeignKey("users.codigo_usuario"), primary_key=True)
    dni_asesor = Column(CHAR(8), unique=True, nullable=False)
    telefono_asesor = Column(CHAR(9))

    usuario = relationship("User", back_populates="asesor_rel")
    
    simulaciones_realizadas = relationship("Simulation", back_populates="asesor_rel")
    unidades_gestionadas = relationship("Unit", back_populates="asesor_rel")
    prospectos = relationship("Prospect", back_populates="asesor_rel")

class Client(Base):
    __tablename__ = "clients"
    codigo_cliente = Column(Integer, ForeignKey("users.codigo_usuario"), primary_key=True)
    dni_cliente = Column(CHAR(8), unique=True, nullable=False)
    telefono_cliente = Column(CHAR(9))
    ingreso_mensual = Column(Numeric(10, 2), default=0.00)
    
    # Nuevos campos
    codigo_tipo_ingreso = Column(Integer, ForeignKey("tipos_ingreso.codigo_tipo_ingreso"), default=1)
    tipo_ingreso_rel = relationship("TipoIngreso", back_populates="clientes")
    
    meses_ahorro = Column(Integer, default=0)
    tiene_deudor_solidario = Column(Boolean, default=False)
    residencia = Column(String(15), default="Peruano") # "Peruano" / "Extranjero"
    
    codigo_estado_civil = Column(Integer, ForeignKey("estados_civil.codigo_estado_civil"), nullable=True)
    estado_civil_rel = relationship("EstadoCivil", back_populates="clientes")
    
    # Datos de Cónyuge/Conviviente
    nombre_conyuge = Column(String(150), nullable=True)
    doc_conyuge = Column(String(12), nullable=True)
    conyuge_propietario = Column(Boolean, default=False)
    ingreso_conyuge = Column(Numeric(10, 2), default=0.00)
    es_propietario_vivienda = Column(Boolean, default=False, nullable=False)
    recibio_apoyo_estatal = Column(Boolean, default=False, nullable=False)
    cantidad_creditos_fmv = Column(Integer, default=0, nullable=False)
    tiene_credito_fmv_activo = Column(Boolean, default=False, nullable=False)
    hijos_menores_propietarios = Column(Boolean, default=False, nullable=False)

    usuario = relationship("User", back_populates="cliente")
    unidades = relationship("Unit", back_populates="propietario")
    simulaciones = relationship("Simulation", back_populates="cliente_rel")

    __table_args__ = (
        CheckConstraint('ingreso_mensual >= 0', name='check_ingreso_mensual_positivo'),
        CheckConstraint('meses_ahorro >= 0', name='check_meses_ahorro_positivo'),
    )

class Prospect(Base):
    __tablename__ = "prospects"
    codigo_prospecto = Column(Integer, primary_key=True, autoincrement=True)
    nombres = Column(String(50), nullable=False)
    apellidos = Column(String(50))
    telefono = Column(String(20), nullable=False)
    email = Column(String(100))
    ingreso_mensual = Column(Numeric(10, 2), default=0.00)
    
    # Nuevos campos (Igual que Cliente)
    codigo_tipo_ingreso = Column(Integer, ForeignKey("tipos_ingreso.codigo_tipo_ingreso"), default=1)
    tipo_ingreso_rel = relationship("TipoIngreso") # Sin back_populates si no es necesario en el maestro
    
    meses_ahorro = Column(Integer, default=0)
    tiene_deudor_solidario = Column(Boolean, default=False)
    residencia = Column(String(15), default="Peruano")
    
    codigo_estado_civil = Column(Integer, ForeignKey("estados_civil.codigo_estado_civil"), nullable=True)
    estado_civil_rel = relationship("EstadoCivil")
    
    nombre_conyuge = Column(String(150), nullable=True)
    doc_conyuge = Column(String(12), nullable=True)
    conyuge_propietario = Column(Boolean, default=False)
    ingreso_conyuge = Column(Numeric(10, 2), default=0.00)
    es_propietario_vivienda = Column(Boolean, default=False, nullable=False)
    recibio_apoyo_estatal = Column(Boolean, default=False, nullable=False)
    cantidad_creditos_fmv = Column(Integer, default=0, nullable=False)
    tiene_credito_fmv_activo = Column(Boolean, default=False, nullable=False)
    hijos_menores_propietarios = Column(Boolean, default=False, nullable=False)

    fecha_registro = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    codigo_asesor = Column(Integer, ForeignKey("advisors.codigo_asesor"), nullable=False)
    asesor_rel = relationship("Advisor", back_populates="prospectos")
    
    unidades = relationship("Unit", back_populates="prospecto_rel")
    simulaciones = relationship("Simulation", back_populates="prospecto_rel")

    __table_args__ = (
        CheckConstraint('ingreso_mensual >= 0', name='check_ingreso_mensual_prospecto_positivo'),
        CheckConstraint('meses_ahorro >= 0', name='check_meses_ahorro_prospecto_positivo'),
    )

class ModalidadVivienda(Base):
    __tablename__ = "modalidades_vivienda"
    codigo_modalidad = Column(Integer, primary_key=True)
    nombre_modalidad = Column(String(20), unique=True, nullable=False) # 'Compra', 'Construccion', 'Mejoramiento'

    unidades = relationship("Unit", back_populates="modalidad_rel")

class TipoVenta(Base):
    __tablename__ = "tipos_venta"
    codigo_tipo_venta = Column(Integer, primary_key=True)
    nombre_tipo_venta = Column(String(20), unique=True, nullable=False) # 'Primera venta', 'Segunda venta'

    unidades = relationship("Unit", back_populates="tipo_venta_rel")

class Unit(Base):
    __tablename__ = "units"
    codigo_unidad = Column(Integer, primary_key=True, autoincrement=True)
    direccion_unidad = Column(String(70), nullable=False)
    distrito_unidad = Column(String(40), nullable=False)
    area_unidad = Column(Numeric(8, 2), default=0.00)
    precio_venta = Column(Numeric(12, 2), default=0.00)
    
    codigo_moneda = Column(Integer, ForeignKey("monedas.codigo_moneda"), nullable=False, default=1)
    moneda_rel = relationship("Moneda", back_populates="unidades")

    # Nuevos campos
    codigo_modalidad = Column(Integer, ForeignKey("modalidades_vivienda.codigo_modalidad"), nullable=False, default=1)
    modalidad_rel = relationship("ModalidadVivienda", back_populates="unidades")
    
    codigo_tipo_venta = Column(Integer, ForeignKey("tipos_venta.codigo_tipo_venta"), nullable=True, default=1)
    tipo_venta_rel = relationship("TipoVenta", back_populates="unidades")
    
    es_sostenible = Column(Boolean, default=False)
    
    fecha_registro = Column(Date, default=date.today, nullable=False)
    
    codigo_estado = Column(Integer, ForeignKey("estados_registro_unidad.codigo_estado"), nullable=False, default=1)
    estado_rel = relationship("EstadoRegistroUnidad", back_populates="unidades")

    foto = Column(String(255))
    
    codigo_cliente = Column(Integer, ForeignKey("clients.codigo_cliente"), nullable=True)
    propietario = relationship("Client", back_populates="unidades")

    codigo_prospecto = Column(Integer, ForeignKey("prospects.codigo_prospecto"), nullable=True)
    prospecto_rel = relationship("Prospect", back_populates="unidades")

    codigo_asesor = Column(Integer, ForeignKey("advisors.codigo_asesor"), nullable=True)
    asesor_rel = relationship("Advisor", back_populates="unidades_gestionadas")

    simulaciones = relationship("Simulation", back_populates="unidad_rel")

    __table_args__ = (
        CheckConstraint('area_unidad > 0', name='check_area_positive'),
        CheckConstraint('precio_venta > 0', name='check_precio_positive'),
    )

class Simulation(Base):
    __tablename__ = "simulations"
    codigo_simulacion = Column(Integer, primary_key=True, autoincrement=True)
    fecha_simulacion = Column(Date, default=date.today, nullable=False)
    fecha_inicio_prestamo = Column(Date, nullable=True)
    cuota_inicial = Column(Numeric(12, 2), default=0.00)
    fecha_inicio_prestamo = Column(Date, nullable=False)

    # Gastos iniciales (Desglose)
    coste_notarial = Column(Numeric(12, 2), default=Decimal("0.00"))
    coste_registral = Column(Numeric(12, 2), default=Decimal("0.00"))
    tasacion = Column(Numeric(12, 2), default=Decimal("0.00"))
    comision_estudio = Column(Numeric(12, 2), default=Decimal("0.00"))
    comision_activacion = Column(Numeric(12, 2), default=Decimal("0.00"))
    
    gastos_iniciales = Column(Numeric(12, 2), default=Decimal("0.00"))
    # Es la suma de los 5 campos anteriores. >= 0 y <= 5% del precio_venta.

    # BBP
    tipo_bbp = Column(String(25), default="Ninguno")
    # "Ninguno" / "Tradicional" / "Sostenible" / "Integrador Tradicional" / "Integrador Sostenible"
    bono_bbp = Column(Numeric(12, 2), default=0.00)  # Monto calculado del bono según tipo_bbp
    categoria_integrador = Column(String(30), nullable=True)
    # Solo si tipo_bbp contiene "Integrador":
    # "Menores ingresos" / "Adulto mayor" / "Discapacidad" / "Desplazado" / "Migrante retornado"
    ingreso_maximo_integrador = Column(Numeric(10, 2), nullable=True)
    # Solo si categoria_integrador = "Menores ingresos" → debe ser <= 4746.00

    # IFI
    ifi_seleccionada = Column(String(50), nullable=True)
    # "BCP" / "BBVA" / "Interbank" / "Pichincha" / "GNB" / NULL (manual)

    # Tasa (directo, ya no FK)
    tipo_tasa = Column(String(15), default="Efectiva")   # "Nominal" / "Efectiva"
    tasa_anual = Column(Numeric(8, 6), default=0.000000)
    capitalizacion = Column(String(15), default="Mensual")
    # Solo si tipo_tasa = "Nominal": "Mensual" / "Bimestral" / "Trimestral"

    plazo_meses = Column(Integer, default=0)  # 60 a 300

    # Gracia (directo, ya no FK)
    tipo_gracia = Column(String(15), default="Ninguno")  # "Ninguno" / "Parcial" / "Total"
    meses_gracia = Column(Integer, default=0)

    # Seguro: TASA aplicada sobre el saldo (no monto fijo)
    seguro_desgravamen = Column(Numeric(8, 6), default=0.000000)

    codigo_unidad = Column(Integer, ForeignKey("units.codigo_unidad"), nullable=False)
    unidad_rel = relationship("Unit", back_populates="simulaciones")
    codigo_cliente = Column(Integer, ForeignKey("clients.codigo_cliente"), nullable=True)
    cliente_rel = relationship("Client", back_populates="simulaciones") 
    codigo_prospecto = Column(Integer, ForeignKey("prospects.codigo_prospecto"), nullable=True)
    prospecto_rel = relationship("Prospect", back_populates="simulaciones")

    codigo_asesor = Column(Integer, ForeignKey("advisors.codigo_asesor"), nullable=True)
    asesor_rel = relationship("Advisor", back_populates="simulaciones_realizadas")

    # RELACIONES A RESULTADOS
    resumen = relationship("SimulationResult", back_populates="simulacion_rel", uselist=False, cascade="all, delete-orphan")
    detalles = relationship("SimulationDetail", back_populates="simulacion_rel", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('tasa_anual > 0', name='check_tasa_anual_positive'),
        CheckConstraint('plazo_meses BETWEEN 60 AND 300', name='check_plazo_meses'),
        CheckConstraint('meses_gracia >= 0 AND meses_gracia < plazo_meses', name='check_meses_gracia'),
        CheckConstraint('seguro_desgravamen >= 0', name='check_seguro_desgravamen'),
        CheckConstraint('cuota_inicial >= 0', name='check_cuota_inicial'),
    )

class SimulationResult(Base):
    __tablename__ = "simulation_results"
    codigo_resumen = Column(Integer, primary_key=True, autoincrement=True)
    codigo_simulacion = Column(Integer, ForeignKey("simulations.codigo_simulacion"), nullable=False)
    
    # ── VARIABLES TÉCNICAS (Según Tabla "Proceso de Simulación") ──
    rango_bbp = Column(String(10)) # "R1", "R2", "R3", "R4", "R5", "SinBBP"
    bono_bbp_base = Column(Numeric(12, 2), default=0.00)
    bono_integrador_adicional = Column(Numeric(12, 2), default=0.00)
    
    precio_neto = Column(Numeric(12, 2), default=0.00)
    monto_financiar = Column(Numeric(12, 2), default=0.00)
    
    # Tasas con precisión (8,6)
    tasa_efectiva_anual = Column(Numeric(8, 6), default=0.000000)
    tasa_efectiva_mensual = Column(Numeric(8, 6), default=0.000000)
    
    factor_frances = Column(Numeric(12, 10), default=0.0000000000)
    cuota_base = Column(Numeric(12, 2), default=0.00) # Cuota sin seguro
    
    # Ratio de elegibilidad
    ratio_cuota_ingreso = Column(Numeric(5, 2), default=0.00) # %
    
    # Indicadores financieros
    van = Column(Numeric(12, 2), default=0.00)
    tir = Column(Numeric(10, 6), default=0.00)
    tcea = Column(Numeric(8, 4), default=0.00)
    
    total_intereses = Column(Numeric(12, 2), default=0.00)
    total_pagado = Column(Numeric(12, 2), default=0.00)
    total_seguro = Column(Numeric(12, 2), default=0.00)

    simulacion_rel = relationship("Simulation", back_populates="resumen")

class SimulationDetail(Base):
    __tablename__ = "simulation_details"
    codigo_simulacion_detalle = Column(Integer, primary_key=True, autoincrement=True)
    codigo_simulacion = Column(Integer, ForeignKey("simulations.codigo_simulacion"), nullable=False)
    
    numero_cuota = Column(Integer, nullable=False)
    saldo_inicio = Column(Numeric(12, 2))
    cuota_total = Column(Numeric(12, 2))
    interes = Column(Numeric(12, 2))
    interes_capitalizado = Column(Numeric(12, 2), default=0.00)
    amortizacion = Column(Numeric(12, 2))
    seguro = Column(Numeric(12, 2))
    saldo_final = Column(Numeric(12, 2))
    flujo_caja = Column(Numeric(12, 2))
    fecha_vencimiento = Column(Date, nullable=True) 

    simulacion_rel = relationship("Simulation", back_populates="detalles")

    __table_args__ = (CheckConstraint('numero_cuota >= 0', name='check_numero_cuota'),)