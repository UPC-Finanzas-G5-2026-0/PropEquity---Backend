from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime
import shutil
import os
from typing import Optional
from app.database import get_db
from app.models import Unit, Client, Moneda, EstadoRegistroUnidad, Prospect, Advisor, User, TipoVenta, BonoBBP
from app.schemas.unit import UnitResponse, UnitUpdate, UnitCreate
from app.core.security import get_current_user

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/json", response_model=UnitResponse)
def add_unit_json(
    unit_in: UnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear unidad usando JSON con validaciones completas"""
    try:
        # VALIDACIONES DE NEGOCIO - DS 004-2025-VIVIENDA
        if unit_in.precio_venta < 68800.00 or unit_in.precio_venta > 488800.00:
            raise HTTPException(
                status_code=422,
                detail=f"El precio debe estar entre S/ 68,800 y S/ 488,800 según DS 004-2025-VIVIENDA. Precio ingresado: S/ {unit_in.precio_venta:,.2f}"
            )
        
        # VALIDACIONES ADICIONALES DE CAMPOS
        if len(unit_in.direccion_unidad) > 70:
            raise HTTPException(
                status_code=422,
                detail="La dirección no puede exceder 70 caracteres"
            )
        
        if len(unit_in.distrito_unidad) > 40:
            raise HTTPException(
                status_code=422,
                detail="El distrito no puede exceder 40 caracteres"
            )
    
        if unit_in.area_unidad <= 0:
            raise HTTPException(
                status_code=422,
                detail="El área debe ser mayor que 0 m²"
            )

        role = current_user.rol_rel.tipo_rol
        
        # Si es cliente, forzamos que la unidad sea suya
        codigo_cliente = unit_in.codigo_cliente
        codigo_asesor = unit_in.codigo_asesor
        codigo_prospecto = unit_in.codigo_prospecto
        
        if role == "Cliente":
            codigo_cliente = current_user.codigo_usuario
            codigo_asesor = None
            codigo_prospecto = None
        
        # Verificar Clientes/Prospectos/Asesores
        if codigo_cliente:
            if not db.query(Client).filter(Client.codigo_cliente == codigo_cliente).first():
                raise HTTPException(status_code=404, detail="Cliente no encontrado.")
        
        if codigo_prospecto:
            if not db.query(Prospect).filter(Prospect.codigo_prospecto == codigo_prospecto).first():
                raise HTTPException(status_code=404, detail="Prospecto no encontrado.")

        if codigo_asesor:
            if not db.query(Advisor).filter(Advisor.codigo_asesor == codigo_asesor).first():
                raise HTTPException(status_code=404, detail="Asesor no encontrado.")

        # Verificar maestros
        if not db.query(Moneda).filter(Moneda.codigo_moneda == unit_in.codigo_moneda).first():
            raise HTTPException(status_code=400, detail="Moneda no válida")
        if not db.query(EstadoRegistroUnidad).filter(EstadoRegistroUnidad.codigo_estado == unit_in.codigo_estado).first():
            raise HTTPException(status_code=400, detail="Estado no válido")

        # Crear registro
        new_unit = Unit(
            direccion_unidad=unit_in.direccion_unidad,
            distrito_unidad=unit_in.distrito_unidad,
            area_unidad=unit_in.area_unidad,
            precio_venta=unit_in.precio_venta,
            codigo_moneda=unit_in.codigo_moneda,
            codigo_modalidad=unit_in.codigo_modalidad,
            codigo_tipo_venta=unit_in.codigo_tipo_venta,
            es_sostenible=unit_in.es_sostenible,
            codigo_estado=unit_in.codigo_estado,
            codigo_cliente=codigo_cliente,
            codigo_prospecto=codigo_prospecto,
            codigo_asesor=codigo_asesor
        )
        db.add(new_unit)
        db.commit()
        db.refresh(new_unit)
        return new_unit
        
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        message = str(e.orig) if getattr(e, "orig", None) else str(e)
        raise HTTPException(
            status_code=400,
            detail=f"Error de integridad en base de datos: {message}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post("/", response_model=UnitResponse)
def add_unit(
    direccion_unidad: str = Form(...),
    distrito_unidad: str = Form(...),
    area_unidad: float = Form(...),
    precio_venta: float = Form(...),
    codigo_moneda: int = Form(1),
    codigo_modalidad: int = Form(1),
    codigo_tipo_venta: Optional[int] = Form(None),
    es_sostenible: bool = Form(False),
    codigo_estado: int = Form(1),
    codigo_cliente: Optional[int] = Form(None),
    codigo_prospecto: Optional[int] = Form(None),
    codigo_asesor: Optional[int] = Form(None),
    foto: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear unidad usando Form data (con foto) - mantiene compatibilidad"""
    try:
        # VALIDACIONES DE NEGOCIO - DS 004-2025-VIVIENDA
        if precio_venta < 68800.00 or precio_venta > 488800.00:
            raise HTTPException(
                status_code=422,
                detail=f"El precio debe estar entre S/ 68,800 y S/ 488,800 según DS 004-2025-VIVIENDA. Precio ingresado: S/ {precio_venta:,.2f}"
            )
        
        # VALIDACIONES DE CAMPOS
        if len(direccion_unidad) > 70:
            raise HTTPException(
                status_code=422,
                detail="La dirección no puede exceder 70 caracteres"
            )
        
        if len(distrito_unidad) > 40:
            raise HTTPException(
                status_code=422,
                detail="El distrito no puede exceder 40 caracteres"
            )
        
        if area_unidad <= 0:
            raise HTTPException(
                status_code=422,
                detail="El área debe ser mayor que 0 m²"
            )

        role = current_user.rol_rel.tipo_rol
        
        # Si es cliente, forzamos que la unidad sea suya
        if role == "Cliente":
            codigo_cliente = current_user.codigo_usuario
            codigo_asesor = None
            codigo_prospecto = None
        
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
            codigo_modalidad=codigo_modalidad,
            codigo_tipo_venta=codigo_tipo_venta,
            es_sostenible=es_sostenible,
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
        
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        message = str(e.orig) if getattr(e, "orig", None) else str(e)
        raise HTTPException(
            status_code=400,
            detail=f"Error de integridad en base de datos: {message}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/", response_model=list[UnitResponse])
def get_units(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Admin/Asesor ven todas. Cliente solo las suyas."""
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente":
        return db.query(Unit).filter(Unit.codigo_cliente == current_user.codigo_usuario).all()
    elif role == "Asesor":
        return db.query(Unit).filter(Unit.codigo_asesor == current_user.codigo_usuario).all()
    return db.query(Unit).all()

@router.get("/client/{codigo_cliente}", response_model=list[UnitResponse])
def get_units_by_client(
    codigo_cliente: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and current_user.codigo_usuario != codigo_cliente:
        raise HTTPException(status_code=403, detail="No puedes ver unidades de otro cliente.")
    return db.query(Unit).filter(Unit.codigo_cliente == codigo_cliente).all()

@router.get("/prospect/{codigo_prospecto}", response_model=list[UnitResponse])
def get_units_by_prospect(
    codigo_prospecto: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente":
        raise HTTPException(status_code=403, detail="No tienes permiso.")
    return db.query(Unit).filter(Unit.codigo_prospecto == codigo_prospecto).all()

@router.get("/advisor/{codigo_asesor}", response_model=list[UnitResponse])
def get_units_by_advisor(
    codigo_asesor: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Asesor solo puede ver sus propias unidades gestionadas."""
    role = current_user.rol_rel.tipo_rol
    if role == "Asesor" and current_user.codigo_usuario != codigo_asesor:
        raise HTTPException(status_code=403, detail="No puedes ver unidades de otro asesor.")
    if role == "Cliente":
        raise HTTPException(status_code=403, detail="No tienes permiso.")
    return db.query(Unit).filter(Unit.codigo_asesor == codigo_asesor).all()

@router.get("/{codigo_unidad}/bbp-options")
def get_bbp_options(
    codigo_unidad: int,
    ifi_seleccionada: Optional[str] = None,   # Si no hay IFI, BBP no aplica
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Devuelve los tipos de BBP disponibles para una unidad.
    ⚠️  El BBP solo aplica con Crédito MiVivienda a través de una IFI.
        Si no se indica ifi_seleccionada, retorna solo ["Ninguno"].

    Opciones EXCLUSIVAS según tipo de vivienda:
      - Tradicional (es_sostenible=false): Ninguno / Tradicional / Integrador Tradicional
      - Sostenible  (es_sostenible=true):  Ninguno / Sostenible  / Integrador Sostenible
    """
    from decimal import Decimal
    unit = db.query(Unit).filter(Unit.codigo_unidad == codigo_unidad).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada.")

    from app.models import ModalidadVivienda
    mod = db.query(ModalidadVivienda).filter(
        ModalidadVivienda.codigo_modalidad == unit.codigo_modalidad
    ).first()
    modalidad = mod.nombre_modalidad if mod else "Compra"
    
    # 🚨 Conversión de Moneda para Validaciones 🚨
    # Usamos un tipo de cambio estándar de 3.75 para esta consulta informativa
    # o podrías hacerlo dinámico si pasas el tipo_cambio por query (opcional)
    tipo_cambio = Decimal("3.75")
    precio_venta = Decimal(str(unit.precio_venta))
    precio_pen = precio_venta
    if unit.moneda_rel and unit.moneda_rel.simbolo_moneda == "USD":
        precio_pen = precio_venta * tipo_cambio

    # Sin IFI (modo manual) → BBP no aplica en absoluto
    if not ifi_seleccionada:
        return {
            "codigo_unidad": codigo_unidad,
            "tipo_vivienda": "Manual - Sin BBP",
            "modalidad": modalidad,
            "precio_venta": float(precio_venta),
            "moneda": unit.moneda_rel.simbolo_moneda if unit.moneda_rel else "PEN",
            "es_sostenible": unit.es_sostenible,
            "tipos_bbp_disponibles": ["Ninguno"],
            "nota": "El BBP solo aplica con Crédito MiVivienda a través de una IFI. Selecciona un banco para ver las opciones."
        }

    # 🚨 RESTRICCIÓN NCMV: Solo Primera Venta 🚨
    tipo_v = db.query(TipoVenta).filter(TipoVenta.codigo_tipo_venta == unit.codigo_tipo_venta).first()
    if tipo_v and tipo_v.nombre_tipo_venta == "Segunda venta":
        return {
            "codigo_unidad": codigo_unidad,
            "tipo_vivienda": "Segunda Venta - Sin BBP",
            "modalidad": modalidad,
            "precio_venta": float(precio_venta),
            "tipos_bbp_disponibles": ["Ninguno"],
            "nota": "El Bono BBP NO aplica para viviendas de segunda venta (usadas)."
        }

    # R5: precio > S/ 488,800 → BBP no aplica
    if precio_pen > Decimal("488800.00"):
        disponibles = ["Ninguno"]
        tipo_vivienda = "R5+ / Fuera de rango"
        nota = "El precio de la vivienda excede el límite máximo para el Bono MiVivienda (S/ 488,800)."

    # Modalidad Mejoramiento → BBP no aplica
    elif modalidad == "Mejoramiento":
        disponibles = ["Ninguno"]
        tipo_vivienda = "Mejoramiento - Sin BBP"
        nota = "El Bono BBP no aplica para modalidad 'Mejoramiento'."

    # Vivienda Sostenible (es_sostenible = true)
    elif unit.es_sostenible:
        disponibles = ["Ninguno", "Sostenible", "Integrador Sostenible"]
        tipo_vivienda = "Vivienda Sostenible"
        nota = "Vivienda certificada. Solo aplican bonos Sostenibles e Integrador Sostenible."

    # Vivienda Tradicional (es_sostenible = false)
    else:
        disponibles = ["Ninguno", "Tradicional", "Integrador Tradicional"]
        tipo_vivienda = "Vivienda Tradicional"
        nota = "Vivienda tradicional. Solo aplican bonos Tradicional e Integrador Tradicional."

    return {
        "codigo_unidad": codigo_unidad,
        "tipo_vivienda": tipo_vivienda,
        "modalidad": modalidad,
        "precio_venta": float(precio_venta),
        "es_sostenible": unit.es_sostenible,
        "tipos_bbp_disponibles": disponibles,
        "nota": nota
    }

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
    codigo_modalidad: Optional[int] = Form(None),
    codigo_tipo_venta: Optional[int] = Form(None),
    es_sostenible: Optional[bool] = Form(None),
    codigo_estado: Optional[int] = Form(None),
    codigo_cliente: Optional[int] = Form(None),
    codigo_prospecto: Optional[int] = Form(None),
    codigo_asesor: Optional[int] = Form(None),
    remove_foto: bool = Form(False),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza una unidad.
    - Administradores: pueden editar cualquier unidad.
    - Asesores: pueden editar las unidades que gestionan.
    - Clientes: pueden editar sus propias unidades.
    """
    try:
        unit = db.query(Unit).filter(Unit.codigo_unidad == codigo_unidad).first()
        if not unit:
            raise HTTPException(status_code=404, detail="Unidad no encontrada")

        role = current_user.rol_rel.tipo_rol
        user_id = current_user.codigo_usuario

        # VALIDACIÓN DE PERMISOS
        if role == "Cliente" and unit.codigo_cliente != user_id:
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar esta unidad.")
        
        if role == "Asesor" and unit.codigo_asesor != user_id:
            # Un asesor solo puede modificar las unidades que tiene asignadas
            # Si un admin se la quitó, ya no puede editarla.
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar esta unidad.")
        
        # Mapear campos que no son nulos
        if direccion_unidad is not None: unit.direccion_unidad = direccion_unidad
        if distrito_unidad is not None: unit.distrito_unidad = distrito_unidad
        if area_unidad is not None: unit.area_unidad = area_unidad
        if precio_venta is not None: unit.precio_venta = precio_venta
        if codigo_moneda is not None: unit.codigo_moneda = codigo_moneda
        if codigo_modalidad is not None: unit.codigo_modalidad = codigo_modalidad
        if codigo_tipo_venta is not None: unit.codigo_tipo_venta = codigo_tipo_venta
        if es_sostenible is not None: unit.es_sostenible = es_sostenible
        if codigo_estado is not None: unit.codigo_estado = codigo_estado
        if codigo_cliente is not None: unit.codigo_cliente = codigo_cliente
        if codigo_prospecto is not None: unit.codigo_prospecto = codigo_prospecto
        if codigo_asesor is not None: unit.codigo_asesor = codigo_asesor

        # Manejar foto
        if remove_foto and not (foto and foto.filename):
            # Usuario eliminó la foto explícitamente
            unit.foto = None
        elif foto and foto.filename:
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

@router.put("/{codigo_unidad}/json", response_model=UnitResponse, tags=["Units"])
def update_unit_json(
    codigo_unidad: int,
    unit_update: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza una unidad usando datos JSON.
    - Administradores: pueden editar cualquier unidad.
    - Asesores: pueden editar las unidades que gestionan.
    - Clientes: pueden editar sus propias unidades.
    """
    try:
        unit = db.query(Unit).filter(Unit.codigo_unidad == codigo_unidad).first()
        if not unit:
            raise HTTPException(status_code=404, detail="Unidad no encontrada")

        role = current_user.rol_rel.tipo_rol
        user_id = current_user.codigo_usuario

        # VALIDACIÓN DE PERMISOS
        if role == "Cliente" and unit.codigo_cliente != user_id:
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar esta unidad.")
        
        if role == "Asesor" and unit.codigo_asesor != user_id:
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar esta unidad.")

        # Actualizar campos desde el objeto Pydantic
        update_data = unit_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(unit, key, value)

        db.commit()
        db.refresh(unit)
        return unit
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")