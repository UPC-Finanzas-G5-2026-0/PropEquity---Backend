from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...database import get_db
from ...models import Unit

router = APIRouter()

@router.get("/")
def list_units(db: Session = Depends(get_db)):
    return db.query(Unit).all()

@router.post("/")
def add_unit(codigo: str, precio: float, db: Session = Depends(get_db)):
    new_unit = Unit(codigo=codigo, precio=precio)
    db.add(new_unit)
    db.commit()
    return new_unit