from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import date, datetime
import shutil
import os
from typing import Optional
from app.database import get_db
from app.models import Unit, Client, Moneda, EstadoRegistroUnidad, Prospect, Advisor
from app.schemas.unit import UnitResponse, UnitUpdate

router = APIRouter()

UPLOAD_DIR = "uploads"
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

from fastapi.encoders import jsonable_encoder

@router.put("/{codigo_unidad}", response_model=UnitResponse)
@router.put("/{codigo_unidad}/", response_model=UnitResponse, include_in_schema=False)
def update_unit(
    codigo_unidad: int,
    direccion_unidad: Optional[str] = Form(None),
    distrito_unidad: Optional[str] = Form(None),
    area_unidad: Optional[float] = Form(None),
    precio_venta: Optional[float] = Form(None),
    codigo_moneda: Optional[int] = Form(None),
    codigo_estado: Optional[int] = Form(None),
    codigo_cliente: Optional[int] = Form(None),
    codigo_prospecto: Optional[int] = Form(None),
    codigo_asesor: Optional[int] = Form(None),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    try:
        unit = db.query(Unit).filter(Unit.codigo_unidad == codigo_unidad).first()
        if not unit:
            raise HTTPException(status_code=404, detail="Unidad no encontrada")
        
        # Mapear campos que no son nulos
        if direccion_unidad is not None: unit.direccion_unidad = direccion_unidad
        if distrito_unidad is not None: unit.distrito_unidad = distrito_unidad
        if area_unidad is not None: unit.area_unidad = area_unidad
        if precio_venta is not None: unit.precio_venta = precio_venta
        if codigo_moneda is not None: unit.codigo_moneda = codigo_moneda
        if codigo_estado is not None: unit.codigo_estado = codigo_estado
        if codigo_cliente is not None: unit.codigo_cliente = codigo_cliente
        if codigo_prospecto is not None: unit.codigo_prospecto = codigo_prospecto
        if codigo_asesor is not None: unit.codigo_asesor = codigo_asesor

        # Manejar nueva foto si se envía
        if foto and foto.filename:
            file_ext = foto.filename.split(".")[-1]
            file_name = f"UNI-{unit.codigo_unidad}.{file_ext}"
            foto_path = os.path.join(UPLOAD_DIR, file_name)
            with open(foto_path, "wb") as buffer:
                shutil.copyfileobj(foto.file, buffer)
            unit.foto = f"/{foto_path}"

        db.commit()
        db.refresh(unit)
        print(f"DEBUG: Unidad {codigo_unidad} actualizada exitosamente. Foto: {unit.foto}")
        return unit
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        with open("error_log.txt", "a") as f:
            f.write(f"\n--- ERROR {datetime.now()} ---\n")
            f.write(traceback.format_exc())
            f.write("\n--------------------------\n")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error - Check error_log.txt")

@router.delete("/{codigo_unidad}")
def delete_unit(codigo_unidad: int, db: Session = Depends(get_db)):
    unit = db.query(Unit).filter(Unit.codigo_unidad == codigo_unidad).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")
    
    db.delete(unit)
    db.commit()
    return {"message": "Unidad eliminada exitosamente"}