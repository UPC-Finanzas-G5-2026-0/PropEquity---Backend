from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...database import get_db
from ...models import Client
from ...schemas.client import ClientCreate, ClientResponse

router = APIRouter()

@router.post("/", response_model=ClientResponse)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    db_client = Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@router.get("/{dni}", response_model=ClientResponse)
def get_client(dni: str, db: Session = Depends(get_db)):
    return db.query(Client).filter(Client.dni == dni).first()