from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import date
import shutil
import os
from typing import Optional
from ...database import get_db
from ...models import Unit, Client, Moneda, EstadoRegistroUnidad, Prospect, Advisor
from ...schemas.unit import UnitResponse

router = APIRouter()

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=UnitResponse)
def add_unit(
    direccion_unidad: str = Form(...),
    distrito_unidad: str = Form(...),
    area_unidad: float = Form(...),
    precio_venta: float = Form(...),
    codigo_moneda: int = Form(1),
    codigo_estado: int = Form(1),
    codigo_cliente: Optional[int] = Form(None),
    codigo_prospecto: Optional[int] = Form(None),
    codigo_asesor: Optional[int] = Form(None),
    foto: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # 1. Verificar Clientes/Prospectos/Asesores
    if codigo_cliente:
        if not db.query(Client).filter(Client.codigo_cliente == codigo_cliente).first():
            raise HTTPException(status_code=404, detail="Cliente no encontrado.")
    
    if codigo_prospecto:
        if not db.query(Prospect).filter(Prospect.codigo_prospecto == codigo_prospecto).first():
            raise HTTPException(status_code=404, detail="Prospecto no encontrado.")

    if codigo_asesor:
        if not db.query(Advisor).filter(Advisor.codigo_asesor == codigo_asesor).first():
            raise HTTPException(status_code=404, detail="Asesor no encontrado.")

    # 2. Verificar maestros
    if not db.query(Moneda).filter(Moneda.codigo_moneda == codigo_moneda).first():
        raise HTTPException(status_code=400, detail="Moneda no válida")
    if not db.query(EstadoRegistroUnidad).filter(EstadoRegistroUnidad.codigo_estado == codigo_estado).first():
        raise HTTPException(status_code=400, detail="Estado no válido")

    # 3. Crear registro
    new_unit = Unit(
        direccion_unidad=direccion_unidad,
        distrito_unidad=distrito_unidad,
        area_unidad=area_unidad,
        precio_venta=precio_venta,
        codigo_moneda=codigo_moneda,
        codigo_estado=codigo_estado,
        codigo_cliente=codigo_cliente,
        codigo_prospecto=codigo_prospecto,
        codigo_asesor=codigo_asesor
    )
    db.add(new_unit)
    db.flush()

    # 4. Guardar foto if exists
    if foto:
        file_ext = foto.filename.split(".")[-1]
        file_name = f"UNI-{new_unit.codigo_unidad}.{file_ext}"
        foto_path = os.path.join(UPLOAD_DIR, file_name)
        with open(foto_path, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)
        new_unit.foto = f"/{foto_path}"

    db.commit()
    db.refresh(new_unit)
    return new_unit

@router.get("/", response_model=list[UnitResponse])
def get_units(db: Session = Depends(get_db)):
    return db.query(Unit).all()

@router.get("/client/{codigo_cliente}", response_model=list[UnitResponse])
def get_units_by_client(codigo_cliente: int, db: Session = Depends(get_db)):
    return db.query(Unit).filter(Unit.codigo_cliente == codigo_cliente).all()

@router.get("/prospect/{codigo_prospecto}", response_model=list[UnitResponse])
def get_units_by_prospect(codigo_prospecto: int, db: Session = Depends(get_db)):
    return db.query(Unit).filter(Unit.codigo_prospecto == codigo_prospecto).all()

@router.get("/advisor/{codigo_asesor}", response_model=list[UnitResponse])
def get_units_by_advisor(codigo_asesor: int, db: Session = Depends(get_db)):
    """Vista de Asesor: Ver unidades que ha captado o gestiona."""
    return db.query(Unit).filter(Unit.codigo_asesor == codigo_asesor).all()