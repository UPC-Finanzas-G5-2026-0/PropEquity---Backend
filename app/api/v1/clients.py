from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db
from ...models import Client
from ...schemas.client import ClientResponse, ClientCreate, ClientUpdate

router = APIRouter()

@router.get("/", response_model=list[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()

@router.get("/{dni_cliente}", response_model=ClientResponse)
def get_client(dni_cliente: str, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.dni_cliente == dni_cliente).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client

@router.get("/code/{codigo_cliente}", response_model=ClientResponse)
def get_client_by_code(codigo_cliente: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.codigo_cliente == codigo_cliente).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client

@router.post("/", response_model=ClientResponse, status_code=201)
def create_client_by_advisor(payload: ClientCreate, db: Session = Depends(get_db)):
    """Alta de un nuevo cliente por parte del Asesor"""
    # 1. Validar que el DNI o Email no existan ya
    if db.query(Client).filter(Client.dni_cliente == payload.dni_cliente).first():
        raise HTTPException(status_code=400, detail="El DNI ya está registrado.")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")

    try:
        # 2. Crear primero el Usuario (Datos personales)
        nuevo_usuario = User(
            nombres=payload.nombres,
            apellidos=payload.apellidos,
            email=payload.email,
            password=get_password_hash(payload.dni_cliente), # Contraseña temporal = su DNI
            codigo_rol=3 # Asumiendo que 3 es el rol de Cliente
        )
        db.add(nuevo_usuario)
        db.flush() # Guardamos temporalmente para obtener el ID generado

        # 3. Crear el Cliente (Datos socioeconómicos) vinculado al usuario
        nuevo_cliente = Client(
            codigo_cliente=nuevo_usuario.codigo_usuario,
            dni_cliente=payload.dni_cliente,
            telefono_cliente=payload.telefono_cliente,
            ingreso_mensual=payload.ingreso_mensual
        )
        db.add(nuevo_cliente)
        db.commit()
        db.refresh(nuevo_cliente)
        return nuevo_cliente

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar cliente: {str(e)}")


@router.put("/{codigo_cliente}", response_model=ClientResponse)
def update_client_info(codigo_cliente: int, payload: ClientUpdate, db: Session = Depends(get_db)):
    """Edición de la información del cliente"""
    # 1. Buscar al cliente
    client = db.query(Client).filter(Client.codigo_cliente == codigo_cliente).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # 2. Actualizar datos de la tabla Client
    if payload.dni_cliente is not None:
        client.dni_cliente = payload.dni_cliente
    if payload.telefono_cliente is not None:
        client.telefono_cliente = payload.telefono_cliente
    if payload.ingreso_mensual is not None:
        client.ingreso_mensual = payload.ingreso_mensual

    # 3. Actualizar datos de la tabla User (nombres)
    if payload.nombres is not None or payload.apellidos is not None:
        if payload.nombres is not None:
            client.usuario_rel.nombres = payload.nombres # Asegúrate de que tu modelo tenga esta relación (usuario_rel o similar)
        if payload.apellidos is not None:
            client.usuario_rel.apellidos = payload.apellidos

    try:
        db.commit()
        db.refresh(client)
        return client
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar cliente: {str(e)}")