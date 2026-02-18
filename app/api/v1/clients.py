from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db
from ...models import Client
from ...schemas.client import ClientResponse

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