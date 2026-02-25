from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr = Field(..., max_length=100)
    nombres: str = Field(..., max_length=50)
    apellidos: str = Field(..., max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    rol_usuario: str = Field("Cliente", pattern="^(Administrador|Asesor|Cliente)$")
    # Campos dinámicos para subtipos
    dni: Optional[str] = Field(None, pattern=r"^\d{8}$")
    telefono: Optional[str] = Field(None, pattern=r"^9\d{8}$") # Debe iniciar en 9 y tener 9 dígitos
    ingreso_mensual: Optional[float] = Field(None, ge=0)
    codigo_tipo_ingreso: Optional[int] = Field(1, ge=1, le=3) # 1:Dependiente, 2:Independiente, 3:Ahorro programado
    meses_ahorro: Optional[int] = Field(0, ge=0)
    tiene_deudor_solidario: Optional[bool] = False
    residencia: Optional[str] = Field("Peruano", pattern="^(Peruano|Extranjero)$")
    codigo_estado_civil: Optional[int] = Field(None, ge=1, le=5) # 1:Soltero, 2:Casado, 3:Conviviente, 4:Divorciado, 5:Viudo
    nombre_conyuge: Optional[str] = Field(None, max_length=150)
    doc_conyuge: Optional[str] = Field(None, max_length=12)
    conyuge_propietario: Optional[bool] = False
    es_propietario_vivienda: Optional[bool] = False

    # Removemos las validaciones personalizadas de Pydantic ya que causaban problemas de serialización
    # Las validaciones de negocio ahora están en el endpoint para mejor manejo de errores

class UserResponse(UserBase):
    codigo_usuario: int
    codigo_rol: int
    fecha_registro: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    nombres: str
    apellidos: str
    codigo_usuario: int
    ingreso_mensual: Optional[float] = None
    es_propietario_vivienda: Optional[bool] = None

class TokenData(BaseModel):
    email: Optional[str] = None