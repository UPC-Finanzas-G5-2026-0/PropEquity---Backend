from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Prospect, Advisor, Client, User
from app.schemas.prospect import ProspectCreate, ProspectResponse, ProspectUpdate
from app.core.security import get_current_user

router = APIRouter()

@router.post("/", response_model=ProspectResponse)
def create_prospect(
    prospect_in: ProspectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Solo Asesores y Administradores pueden crear prospectos."""
    role = current_user.rol_rel.tipo_rol
    if role not in ["Administrador", "Asesor"]:
        raise HTTPException(status_code=403, detail="Solo asesores pueden registrar prospectos.")

    # Si es Asesor, forzar su propio codigo como codigo_asesor
    if role == "Asesor":
        prospect_in.codigo_asesor = current_user.codigo_usuario

    advisor = db.query(Advisor).filter(Advisor.codigo_asesor == prospect_in.codigo_asesor).first()
    if not advisor:
        raise HTTPException(status_code=404, detail="Asesor no encontrado.")

    new_prospect = Prospect(**prospect_in.model_dump())
    db.add(new_prospect)
    db.commit()
    db.refresh(new_prospect)
    return new_prospect

@router.get("/", response_model=list[ProspectResponse])
def get_prospects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    - Administrador: ve todos los prospectos.
    - Asesor: solo ve sus propios prospectos.
    - Cliente: no tiene acceso.
    """
    role = current_user.rol_rel.tipo_rol
    if role == "Administrador":
        return db.query(Prospect).all()
    elif role == "Asesor":
        return db.query(Prospect).filter(Prospect.codigo_asesor == current_user.codigo_usuario).all()
    else:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver prospectos.")

@router.get("/me", response_model=list[ProspectResponse])
def get_my_prospects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Asesor autenticado ve solo sus prospectos."""
    role = current_user.rol_rel.tipo_rol
    if role != "Asesor":
        raise HTTPException(status_code=403, detail="Solo asesores pueden usar este endpoint.")
    return db.query(Prospect).filter(Prospect.codigo_asesor == current_user.codigo_usuario).all()

@router.get("/{codigo_prospecto}", response_model=ProspectResponse)
def get_prospect(
    codigo_prospecto: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Un asesor solo puede ver los prospectos que él registró."""
    role = current_user.rol_rel.tipo_rol
    prospect = db.query(Prospect).filter(Prospect.codigo_prospecto == codigo_prospecto).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospecto no encontrado.")

    if role == "Asesor" and prospect.codigo_asesor != current_user.codigo_usuario:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver este prospecto.")
    if role == "Cliente":
        raise HTTPException(status_code=403, detail="No tienes permiso.")
    return prospect

@router.get("/advisor/{codigo_asesor}", response_model=list[ProspectResponse])
def get_prospects_by_advisor(
    codigo_asesor: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Un asesor solo puede ver sus propios prospectos. Admin puede ver de cualquiera."""
    role = current_user.rol_rel.tipo_rol
    if role == "Asesor" and current_user.codigo_usuario != codigo_asesor:
        raise HTTPException(status_code=403, detail="Solo puedes ver tus propios prospectos.")
    if role == "Cliente":
        raise HTTPException(status_code=403, detail="No tienes permiso.")
    return db.query(Prospect).filter(Prospect.codigo_asesor == codigo_asesor).all()

@router.put("/{codigo_prospecto}", response_model=ProspectResponse)
def update_prospect(
    codigo_prospecto: int,
    prospect_in: ProspectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Solo el asesor que creó el prospecto (o el Admin) puede editarlo."""
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente":
        raise HTTPException(status_code=403, detail="No tienes permiso.")

    prospect = db.query(Prospect).filter(Prospect.codigo_prospecto == codigo_prospecto).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospecto no encontrado.")

    if role == "Asesor" and prospect.codigo_asesor != current_user.codigo_usuario:
        raise HTTPException(status_code=403, detail="No puedes editar prospectos de otro asesor.")

    update_data = prospect_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(prospect, key, value)

    db.commit()
    db.refresh(prospect)
    return prospect

@router.delete("/{codigo_prospecto}")
def delete_prospect(
    codigo_prospecto: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Solo el asesor que creó el prospecto (o el Admin) puede eliminarlo."""
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente":
        raise HTTPException(status_code=403, detail="No tienes permiso.")

    prospect = db.query(Prospect).filter(Prospect.codigo_prospecto == codigo_prospecto).first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospecto no encontrado.")

    if role == "Asesor" and prospect.codigo_asesor != current_user.codigo_usuario:
        raise HTTPException(status_code=403, detail="No puedes eliminar prospectos de otro asesor.")

    db.delete(prospect)
    db.commit()
    return {"message": "Prospecto eliminado exitosamente."}
