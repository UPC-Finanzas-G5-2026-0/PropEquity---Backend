from fastapi import APIRouter, Depends, HTTPException, Path, Body
from sqlalchemy.orm import Session, joinedload
from ...database import get_db
from ...models import Client, User
from ...schemas.client import ClientResponse, ClientCreate, ClientUpdate
from ...core.security import get_current_user, get_password_hash

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

@router.post("/", response_model=ClientResponse, status_code=201)
def create_client_by_advisor(
    payload: ClientCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Alta de un nuevo cliente por parte del Asesor"""
    # 1. Validar permisos
    role = current_user.rol_rel.tipo_rol
    if role not in ["Administrador", "Asesor"]:
        raise HTTPException(status_code=403, detail="Solo los asesores pueden dar de alta a clientes directamente.")

    # 2. Validar duplicidad
    if db.query(Client).filter(Client.dni_cliente == payload.dni_cliente).first():
        raise HTTPException(status_code=400, detail="El DNI ya está registrado en el sistema.")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado.")

    try:
        # 3. Crear Usuario
        nuevo_usuario = User(
            nombres=payload.nombres,
            apellidos=payload.apellidos,
            email=payload.email,
            password=get_password_hash(payload.dni_cliente), # El DNI funciona como contraseña inicial
            codigo_rol=3 # Rol de Cliente
        )
        db.add(nuevo_usuario)
        db.flush()

        # 4. Crear Cliente
        nuevo_cliente = Client(
            codigo_cliente=nuevo_usuario.codigo_usuario,
            dni_cliente=payload.dni_cliente,
            telefono_cliente=payload.telefono_cliente,
            ingreso_mensual=payload.ingreso_mensual,
            codigo_tipo_ingreso=payload.codigo_tipo_ingreso,
            meses_ahorro=payload.meses_ahorro,
            tiene_deudor_solidario=payload.tiene_deudor_solidario,
            residencia=payload.residencia,
            codigo_estado_civil=payload.codigo_estado_civil,
            nombre_conyuge=payload.nombre_conyuge,
            doc_conyuge=payload.doc_conyuge,
            conyuge_propietario=payload.conyuge_propietario,
            es_propietario_vivienda=payload.es_propietario_vivienda
        )
        db.add(nuevo_cliente)
        db.commit()
        
        return _load_client(db.query(Client)).filter(Client.codigo_cliente == nuevo_cliente.codigo_cliente).first()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar cliente: {str(e)}")

@router.put("/update/{codigo_cliente}", response_model=ClientResponse)
def update_client(
    codigo_cliente: int = Path(..., title="The ID of the client to update"),
    client_in: ClientUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Solo el mismo cliente o un Administrador/Asesor puede actualizar el perfil."""
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and current_user.codigo_usuario != codigo_cliente:
        raise HTTPException(status_code=403, detail="No puedes modificar el perfil de otro cliente.")

    client = db.query(Client).options(joinedload(Client.usuario)).filter(
        Client.codigo_cliente == codigo_cliente
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Actualizar campos de Cliente
    for field, value in client_in.dict(exclude_unset=True).items():
        if hasattr(client, field) and value is not None:
            setattr(client, field, value)

    # Actualizar campos de Usuario vinculados
    if client_in.nombres is not None:
        client.usuario.nombres = client_in.nombres
    if client_in.apellidos is not None:
        client.usuario.apellidos = client_in.apellidos

    try:
        db.commit()
        db.refresh(client)
        db.refresh(client.usuario)
        return _load_client(db.query(Client)).filter(Client.codigo_cliente == codigo_cliente).first()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar cliente: {str(e)}")

@router.get("/code/{codigo_cliente}", response_model=ClientResponse)
def get_client_by_code(
    codigo_cliente: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Un cliente solo puede ver su propio perfil. Admins/Asesores pueden ver cualquiera."""
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and current_user.codigo_usuario != codigo_cliente:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver el perfil de otro cliente.")

    client = _load_client(db.query(Client)).filter(Client.codigo_cliente == codigo_cliente).first()
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
    client = _load_client(db.query(Client)).filter(Client.dni_cliente == dni_cliente).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and current_user.codigo_usuario != client.codigo_cliente:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver el perfil de otro cliente.")
    return client