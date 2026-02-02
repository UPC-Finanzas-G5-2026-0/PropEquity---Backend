from pydantic import BaseModel, Field

class ClientBase(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=50)
    dni: str = Field(..., pattern=r"^\d{8}$") # Restricción de 8 dígitos
    ingreso_neto: float = Field(..., gt=0)
    telefono: str = Field(..., min_length=9)

class ClientCreate(ClientBase):
    pass

class ClientResponse(ClientBase):
    id: int
    class Config:
        from_attributes = True