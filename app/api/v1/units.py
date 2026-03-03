from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime
import os
from typing import Optional

import cloudinary
import cloudinary.uploader

from app.database import get_db
from app.models import Unit, Client, Moneda, EstadoRegistroUnidad, Prospect, Advisor, User, TipoVenta, BonoBBP, ModalidadVivienda
from app.schemas.unit import UnitResponse, UnitUpdate, UnitCreate
from app.core.security import get_current_user

router = APIRouter()

# CONFIGURACIÓN DE CLOUDINARY (Lee las credenciales ocultas en Render)
cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.getenv("CLOUDINARY_API_KEY"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET") 
)

@router.post("/json", response_model=UnitResponse)
def add_unit_json(
    unit_in: UnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear unidad usando JSON con validaciones completas"""
    try:
        # Candado de seguridad: Permitimos registro si es Admin, Asesor o Cliente (que se asigna a sí mismo)
        role = current_user.rol_rel.tipo_rol
        if role not in ["Administrador", "Asesor", "Cliente"]:
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado. El rol no tiene permisos de registro."
            )

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
        
        # Si es cliente, forzamos que la unidad sea suya (Aunque aquí solo entra Admin, lo dejamos por seguridad)
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
    """Crear unidad usando Form data (con foto en Cloudinary)"""
    try:
        # Candado de seguridad: Registro permitido para todos los roles válidos
        role = current_user.rol_rel.tipo_rol
        if role not in ["Administrador", "Asesor", "Cliente"]:
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado. El rol no tiene permisos de registro."
            )

        # VALIDACIONES DE NEGOCIO
        if precio_venta < 68800.00 or precio_venta > 488800.00:
            raise HTTPException(
                status_code=422,
                detail=f"El precio debe estar entre S/ 68,800 y S/ 488,800. Precio ingresado: S/ {precio_venta:,.2f}"
            )
        
        # VALIDACIONES DE CAMPOS
        if len(direccion_unidad) > 70:
            raise HTTPException(status_code=422, detail="La dirección no puede exceder 70 caracteres")
        if len(distrito_unidad) > 40:
            raise HTTPException(status_code=422, detail="El distrito no puede exceder 40 caracteres")
        if area_unidad <= 0:
            raise HTTPException(status_code=422, detail="El área debe ser mayor que 0 m²")

        if role == "Cliente":
            codigo_cliente = current_user.codigo_usuario
            codigo_asesor = None
            codigo_prospecto = None
        
        # Verificar Clientes/Prospectos/Asesores/Maestros
        if codigo_cliente and not db.query(Client).filter(Client.codigo_cliente == codigo_cliente).first():
            raise HTTPException(status_code=404, detail="Cliente no encontrado.")
        if codigo_prospecto and not db.query(Prospect).filter(Prospect.codigo_prospecto == codigo_prospecto).first():
            raise HTTPException(status_code=404, detail="Prospecto no encontrado.")
        if codigo_asesor and not db.query(Advisor).filter(Advisor.codigo_asesor == codigo_asesor).first():
            raise HTTPException(status_code=404, detail="Asesor no encontrado.")
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

        # 4. 🚨 GUARDAR FOTO EN CLOUDINARY
        if foto and foto.filename:
            try:
                # Subimos el archivo a la nube en la carpeta propequity
                result = cloudinary.uploader.upload(foto.file, folder="propequity/unidades")
                # Guardamos la URL pública segura que nos da Cloudinary
                new_unit.foto = result.get("secure_url")
            except Exception as e:
                print(f"Error subiendo imagen a Cloudinary: {e}")
                # Si falla la imagen, la dejamos vacía pero no rompemos la creación de la unidad
                new_unit.foto = None

        db.commit()
        db.refresh(new_unit)
        return new_unit
        
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        message = str(e.orig) if getattr(e, "orig", None) else str(e)
        raise HTTPException(status_code=400, detail=f"Error de integridad en base de datos: {message}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/", response_model=list[UnitResponse])
def get_units(
    solo_mias: bool = False,
    solo_mis_y_favoritos: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models import UnitFavorite
    role = current_user.rol_rel.tipo_rol
    user_id = current_user.codigo_usuario
    
    query = db.query(Unit)
    
    # Si se pide solo mis unidades (Catálogo Personal)
    if solo_mias:
        if role == "Cliente":
            query = query.filter(Unit.codigo_cliente == user_id)
        elif role == "Asesor":
            query = query.filter(Unit.codigo_asesor == user_id)

    # Si se pide solo mis unidades + favoritos (Para el Simulador)
    elif solo_mis_y_favoritos:
        from sqlalchemy import or_
        # Obtenemos IDs de sus favoritos
        favorites_ids = [f.codigo_unidad for f in db.query(UnitFavorite).filter(UnitFavorite.codigo_usuario == user_id).all()]
        
        if role == "Cliente":
            query = query.filter(or_(Unit.codigo_cliente == user_id, Unit.codigo_unidad.in_(favorites_ids)))
        elif role == "Asesor":
            query = query.filter(or_(Unit.codigo_asesor == user_id, Unit.codigo_unidad.in_(favorites_ids)))
        else:
            # Para Admin, mostrar todas por ahora o las suyas si tuviera
            pass

    units = query.all()
    
    # Marcar 'es_favorito' en cada unidad
    fav_ids = set(f.codigo_unidad for f in db.query(UnitFavorite).filter(UnitFavorite.codigo_usuario == user_id).all())
    for u in units:
        u.es_favorito = u.codigo_unidad in fav_ids
        
    return units


@router.post("/{codigo_unidad}/favorite")
def toggle_favorite(
    codigo_unidad: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models import UnitFavorite
    user_id = current_user.codigo_usuario
    
    existing = db.query(UnitFavorite).filter(
        UnitFavorite.codigo_usuario == user_id,
        UnitFavorite.codigo_unidad == codigo_unidad
    ).first()
    
    if existing:
        db.delete(existing)
        db.commit()
        return {"success": True, "message": "Eliminado de favoritos", "es_favorito": False}
    else:
        new_fav = UnitFavorite(codigo_usuario=user_id, codigo_unidad=codigo_unidad)
        db.add(new_fav)
        db.commit()
        return {"success": True, "message": "Agregado a favoritos", "es_favorito": True}


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
    role = current_user.rol_rel.tipo_rol
    if role == "Asesor" and current_user.codigo_usuario != codigo_asesor:
        raise HTTPException(status_code=403, detail="No puedes ver unidades de otro asesor.")
    if role == "Cliente":
        raise HTTPException(status_code=403, detail="No tienes permiso.")
    return db.query(Unit).filter(Unit.codigo_asesor == codigo_asesor).all()


@router.get("/{codigo_unidad}/bbp-options")
def get_bbp_options(
    codigo_unidad: int,
    ifi_seleccionada: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from decimal import Decimal
    unit = db.query(Unit).filter(Unit.codigo_unidad == codigo_unidad).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada.")

    from app.models import ModalidadVivienda
    mod = db.query(ModalidadVivienda).filter(
        ModalidadVivienda.codigo_modalidad == unit.codigo_modalidad
    ).first()
    modalidad = mod.nombre_modalidad if mod else "Compra"
    
    tipo_cambio = Decimal("3.75")
    precio_venta = Decimal(str(unit.precio_venta))
    precio_pen = precio_venta
    if unit.moneda_rel and unit.moneda_rel.simbolo_moneda == "USD":
        precio_pen = precio_venta * tipo_cambio

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

    if precio_pen > Decimal("488800.00"):
        disponibles = ["Ninguno"]
        tipo_vivienda = "R5+ / Fuera de rango"
        nota = "El precio de la vivienda excede el límite máximo para el Bono MiVivienda (S/ 488,800)."

    elif modalidad == "Mejoramiento":
        disponibles = ["Ninguno"]
        tipo_vivienda = "Mejoramiento - Sin BBP"
        nota = "El Bono BBP no aplica para modalidad 'Mejoramiento'."

    elif unit.es_sostenible:
        disponibles = ["Ninguno", "Sostenible", "Integrador Sostenible"]
        tipo_vivienda = "Vivienda Sostenible"
        nota = "Vivienda certificada. Solo aplican bonos Sostenibles e Integrador Sostenible."

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
    """Actualiza una unidad (soporta reemplazar foto a Cloudinary)"""
    try:
        unit = db.query(Unit).filter(Unit.codigo_unidad == codigo_unidad).first()
        if not unit:
            raise HTTPException(status_code=404, detail="Unidad no encontrada")

        # VALIDACIÓN DE PERMISOS (Restaurado a acceso abierto para roles válidos)
        role = current_user.rol_rel.tipo_rol
        if role not in ["Administrador", "Asesor", "Cliente"]:
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar unidades.")
        
        # Mapear campos
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

        # 🚨 MANEJO DE FOTO CON CLOUDINARY
        if remove_foto and not (foto and foto.filename):
            unit.foto = None
        elif foto and foto.filename:
            try:
                result = cloudinary.uploader.upload(foto.file, folder="propequity/unidades")
                unit.foto = result.get("secure_url")
            except Exception as e:
                print(f"Error subiendo imagen a Cloudinary: {e}")

        db.commit()
        db.refresh(unit)
        return unit
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.put("/{codigo_unidad}/json", response_model=UnitResponse, tags=["Units"])
def update_unit_json(
    codigo_unidad: int,
    unit_update: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        unit = db.query(Unit).filter(Unit.codigo_unidad == codigo_unidad).first()
        if not unit:
            raise HTTPException(status_code=404, detail="Unidad no encontrada")

        role = current_user.rol_rel.tipo_rol
        if role not in ["Administrador", "Asesor", "Cliente"]:
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar esta unidad.")

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


@router.delete("/{codigo_unidad}")
def delete_unit(
    codigo_unidad: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        role = current_user.rol_rel.tipo_rol
        if role not in ["Administrador", "Asesor", "Cliente"]:
             raise HTTPException(status_code=403, detail="No tienes permiso para eliminar unidades.")

        unit = db.query(Unit).filter(Unit.codigo_unidad == codigo_unidad).first()
            
        db.delete(unit)
        db.commit()
        return {"success": True, "message": "Unidad eliminada correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")