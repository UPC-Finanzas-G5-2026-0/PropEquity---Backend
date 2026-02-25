from fastapi import APIRouter, Depends, HTTPException, Path, Body
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Client, User
from app.schemas.client import ClientResponse, ClientUpdate
from app.core.security import get_current_user

router = APIRouter()

def _load_client(query):
    """Helper: aplica joinedload para siempre cargar relaciones."""
    return query.options(
        joinedload(Client.usuario),
        joinedload(Client.unidades),
        joinedload(Client.simulaciones)
    )

@router.get("/", response_model=list[ClientResponse])
def list_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Solo accesible por Administradores o Asesores."""
    if current_user.rol_rel.tipo_rol not in ["Administrador", "Asesor"]:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver todos los clientes.")
    return _load_client(db.query(Client)).all()

@router.get("/me", response_model=ClientResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """El cliente autenticado ve su propio perfil con sus unidades y simulaciones."""
    client = _load_client(db.query(Client)).filter(
        Client.codigo_cliente == current_user.codigo_usuario
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Perfil de cliente no encontrado.")
    return client

# IMPORTANTE: definir rutas específicas ANTES de la ruta genérica /{dni_cliente}
@router.get("/code/{codigo_cliente}", response_model=ClientResponse)
def get_client_by_code(
    codigo_cliente: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Un cliente solo puede ver su propio perfil. Admins/Asesores pueden ver cualquiera."""
    from sqlalchemy.orm import joinedload

    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and current_user.codigo_usuario != codigo_cliente:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver el perfil de otro cliente.")

    client = _load_client(db.query(Client)).filter(
        Client.codigo_cliente == codigo_cliente
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client

@router.get("/{dni_cliente}", response_model=ClientResponse)
def get_client(
    dni_cliente: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Buscar por DNI. Solo admin/asesor, o el propio cliente."""
    client = _load_client(db.query(Client)).filter(
        Client.dni_cliente == dni_cliente
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and current_user.codigo_usuario != client.codigo_cliente:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver el perfil de otro cliente.")
    return client

@router.put("/update/{codigo_cliente}", response_model=ClientResponse)
def update_client(
    codigo_cliente: int = Path(..., title="The ID of the client to update"),
    client_in: ClientUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Solo el mismo cliente o un Administrador puede actualizar el perfil."""
    from sqlalchemy.orm import joinedload

    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and current_user.codigo_usuario != codigo_cliente:
        raise HTTPException(status_code=403, detail="No puedes modificar el perfil de otro cliente.")

    client = db.query(Client).options(joinedload(Client.usuario)).filter(
        Client.codigo_cliente == codigo_cliente
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if client_in.dni_cliente is not None:
        client.dni_cliente = client_in.dni_cliente
    if client_in.telefono_cliente is not None:
        client.telefono_cliente = client_in.telefono_cliente
    if client_in.ingreso_mensual is not None:
        client.ingreso_mensual = client_in.ingreso_mensual
    if client_in.codigo_tipo_ingreso is not None:
        client.codigo_tipo_ingreso = client_in.codigo_tipo_ingreso
    if client_in.meses_ahorro is not None:
        client.meses_ahorro = client_in.meses_ahorro
    if client_in.tiene_deudor_solidario is not None:
        client.tiene_deudor_solidario = client_in.tiene_deudor_solidario
    if client_in.residencia is not None:
        client.residencia = client_in.residencia
    if client_in.codigo_estado_civil is not None:
        client.codigo_estado_civil = client_in.codigo_estado_civil
    if client_in.nombre_conyuge is not None:
        client.nombre_conyuge = client_in.nombre_conyuge
    if client_in.doc_conyuge is not None:
        client.doc_conyuge = client_in.doc_conyuge
    if client_in.conyuge_propietario is not None:
        client.conyuge_propietario = client_in.conyuge_propietario
    if client_in.es_propietario_vivienda is not None:
        client.es_propietario_vivienda = client_in.es_propietario_vivienda

    # Update User fields
    if client_in.nombres is not None:
        client.usuario.nombres = client_in.nombres
    if client_in.apellidos is not None:
        client.usuario.apellidos = client_in.apellidos

    db.commit()
    db.refresh(client)
    db.refresh(client.usuario)
    return client