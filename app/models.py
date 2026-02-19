from datetime import date, datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Numeric, Date, DateTime, CheckConstraint, CHAR, Boolean
from sqlalchemy.orm import relationship
from .database import Base

class Moneda(Base):
    __tablename__ = "monedas"
    codigo_moneda = Column(Integer, primary_key=True)
    simbolo_moneda = Column(CHAR(3), unique=True, nullable=False) # 'PEN', 'USD'
    tipo_moneda = Column(String(20), nullable=False) # 'Soles', 'Dólares'

    unidades = relationship("Unit", back_populates="moneda_rel")

class EstadoRegistroUnidad(Base):
    __tablename__ = "estados_registro_unidad"
    codigo_estado = Column(Integer, primary_key=True)
    tipo_estado = Column(String(10), unique=True, nullable=False) # 'Activo', 'Inactivo'

    unidades = relationship("Unit", back_populates="estado_rel")

class RolUsuario(Base):
    __tablename__ = "roles_usuario"
    codigo_rol = Column(Integer, primary_key=True, autoincrement=True)
    tipo_rol = Column(String(15), unique=True, nullable=False) # 'Administrador', 'Asesor', 'Cliente'

    usuarios = relationship("User", back_populates="rol_rel")

class TipoTasa(Base):
    __tablename__ = "tipos_tasa"
    codigo_tipo_tasa = Column(Integer, primary_key=True)
    tipo = Column(String(15), unique=True, nullable=False) # 'Nominal', 'Efectiva'

    simulaciones = relationship("Simulation", back_populates="tipo_tasa_rel")

class TipoGracia(Base):
    __tablename__ = "tipos_gracia"
    codigo_tipo_gracia = Column(Integer, primary_key=True)
    tipo = Column(String(15), unique=True, nullable=False) # 'Ninguno', 'Parcial', 'Total'

    simulaciones = relationship("Simulation", back_populates="tipo_gracia_rel")

class User(Base):
    __tablename__ = "users"
    codigo_usuario = Column(Integer, primary_key=True, autoincrement=True)
    nombres = Column(String(50), nullable=False)
    apellidos = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(60), nullable=False)
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

    usuario = relationship("User", back_populates="cliente")
    unidades = relationship("Unit", back_populates="propietario")
    simulaciones = relationship("Simulation", back_populates="cliente_rel")

    __table_args__ = (CheckConstraint('ingreso_mensual >= 0', name='check_ingreso_mensual_positivo'),)

class Prospect(Base):
    __tablename__ = "prospects"
    codigo_prospecto = Column(Integer, primary_key=True, autoincrement=True)
    nombres = Column(String(50), nullable=False)
    apellidos = Column(String(50))
    telefono = Column(String(20), nullable=False)
    email = Column(String(100))
    ingreso_mensual = Column(Numeric(10, 2), default=0.00)
    fecha_registro = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    codigo_asesor = Column(Integer, ForeignKey("advisors.codigo_asesor"), nullable=False)
    asesor_rel = relationship("Advisor", back_populates="prospectos")
    
    unidades = relationship("Unit", back_populates="prospecto_rel")
    simulaciones = relationship("Simulation", back_populates="prospecto_rel")

    __table_args__ = (CheckConstraint('ingreso_mensual >= 0', name='check_ingreso_mensual_prospecto_positivo'),)

class Unit(Base):
    __tablename__ = "units"
    codigo_unidad = Column(Integer, primary_key=True, autoincrement=True)
    direccion_unidad = Column(String(70), nullable=False)
    distrito_unidad = Column(String(40), nullable=False)
    area_unidad = Column(Numeric(8, 2), default=0.00)
    precio_venta = Column(Numeric(12, 2), default=0.00)
    
    codigo_moneda = Column(Integer, ForeignKey("monedas.codigo_moneda"), nullable=False, default=1)
    moneda_rel = relationship("Moneda", back_populates="unidades")

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
    cuota_inicial = Column(Numeric(12, 2), default=0.00)
    bono_bbp = Column(Numeric(12, 2), default=0.00)
    
    codigo_tipo_tasa = Column(Integer, ForeignKey("tipos_tasa.codigo_tipo_tasa"), nullable=False, default=2)
    tipo_tasa_rel = relationship("TipoTasa", back_populates="simulaciones")

    tasa_anual = Column(Numeric(8, 6), default=0.000000)
    capitalizacion = Column(String(15), default="Mensual")
    plazo_meses = Column(Integer, default=0)
    
    codigo_tipo_gracia = Column(Integer, ForeignKey("tipos_gracia.codigo_tipo_gracia"), nullable=False, default=1)
    tipo_gracia_rel = relationship("TipoGracia", back_populates="simulaciones")

    meses_gracia = Column(Integer, default=0)
    seguro_desgravamen = Column(Numeric(8, 2), default=0.00)
    
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
        CheckConstraint('plazo_meses BETWEEN 48 AND 300', name='check_plazo_meses'),
        CheckConstraint('meses_gracia >= 0 AND meses_gracia < plazo_meses', name='check_meses_gracia'),
        CheckConstraint('seguro_desgravamen >= 0', name='check_seguro_desgravamen'),
        CheckConstraint('cuota_inicial >= 0', name='check_cuota_inicial'),
    )

class SimulationResult(Base):
    __tablename__ = "simulation_results"
    codigo_simulacion = Column(Integer, ForeignKey("simulations.codigo_simulacion"), primary_key=True)
    
    # Intermedios
    precio_neto = Column(Numeric(12, 2))
    monto_financiar = Column(Numeric(12, 2))
    tasa_periodica = Column(Numeric(10, 8))
    tasa_efectiva_mensual = Column(Numeric(10, 8))
    factor_frances = Column(Numeric(12, 10))

    # Indicadores Finales (Outputs)
    van = Column(Numeric(12, 2))
    tir = Column(Numeric(10, 8))
    tcea = Column(Numeric(8, 4))
    total_intereses = Column(Numeric(12, 2))
    total_pagado = Column(Numeric(12, 2))
    total_seguro = Column(Numeric(12, 2))

    simulacion_rel = relationship("Simulation", back_populates="resumen")

class SimulationDetail(Base):
    __tablename__ = "simulation_details"
    codigo_simulacion_detalle = Column(Integer, primary_key=True, autoincrement=True)
    codigo_simulacion = Column(Integer, ForeignKey("simulations.codigo_simulacion"), nullable=False)
    
    numero_cuota = Column(Integer, nullable=False)
    cuota_total = Column(Numeric(12, 2))
    interes = Column(Numeric(12, 2))
    amortizacion = Column(Numeric(12, 2))
    seguro = Column(Numeric(12, 2))
    saldo_final = Column(Numeric(12, 2))

    simulacion_rel = relationship("Simulation", back_populates="detalles")

    __table_args__ = (CheckConstraint('numero_cuota >= 1', name='check_numero_cuota'),)
