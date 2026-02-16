from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    
    first_name = Column(String)
    last_name = Column(String)
    
    role = Column(String, default="asesor")
    is_active = Column(Boolean, default=True)

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    dni = Column(String(8), unique=True)
    ingreso_neto = Column(Float)

class Unit(Base):
    __tablename__ = "units"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True)
    precio = Column(Float)
    direccion = Column(String)