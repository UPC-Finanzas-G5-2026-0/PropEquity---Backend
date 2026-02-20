from fastapi import APIRouter, Depends, HTTPException, Path, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Client
from app.schemas.client import ClientResponse, ClientUpdate

router = APIRouter()

@router.get("/", response_model=list[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    return db.query(Client).options(joinedload(Client.usuario)).all()

@router.get("/{dni_cliente}", response_model=ClientResponse)
def get_client(dni_cliente: str, db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    client = db.query(Client).options(joinedload(Client.usuario)).filter(Client.dni_cliente == dni_cliente).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client

@router.put("/update/{codigo_cliente}", response_model=ClientResponse)
def update_client(codigo_cliente: int = Path(..., title="The ID of the client to update"), client_in: ClientUpdate = Body(...), db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    client = db.query(Client).options(joinedload(Client.usuario)).filter(Client.codigo_cliente == codigo_cliente).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if client_in.dni_cliente is not None:
        client.dni_cliente = client_in.dni_cliente
    if client_in.telefono_cliente is not None:
        client.telefono_cliente = client_in.telefono_cliente
    if client_in.ingreso_mensual is not None:
        client.ingreso_mensual = client_in.ingreso_mensual
    
    # Update User fields
    if client_in.nombres is not None:
        client.usuario.nombres = client_in.nombres
    if client_in.apellidos is not None:
        client.usuario.apellidos = client_in.apellidos

    db.commit()
    db.refresh(client)
    # Refresh user to ensure nested data is up to date
    db.refresh(client.usuario)
    return client

@router.get("/code/{codigo_cliente}", response_model=ClientResponse)
def get_client_by_code(codigo_cliente: int, db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    client = db.query(Client).options(joinedload(Client.usuario)).filter(Client.codigo_cliente == codigo_cliente).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client