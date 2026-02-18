from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...database import get_db
from ...models import Prospect, Advisor
from ...schemas.prospect import ProspectCreate, ProspectResponse

router = APIRouter()

@router.post("/", response_model=ProspectResponse)
def create_prospect(prospect_in: ProspectCreate, db: Session = Depends(get_db)):
    # 1. Verificar asesor
    advisor = db.query(Advisor).filter(Advisor.codigo_asesor == prospect_in.codigo_asesor).first()
    if not advisor:
        raise HTTPException(status_code=404, detail="Asesor no encontrado.")

    # 2. Crear prospecto
    new_prospect = Prospect(**prospect_in.dict())
    db.add(new_prospect)
    db.commit()
    db.refresh(new_prospect)
    return new_prospect

@router.get("/", response_model=list[ProspectResponse])
def get_prospects(db: Session = Depends(get_db)):
    return db.query(Prospect).all()

@router.get("/advisor/{codigo_asesor}", response_model=list[ProspectResponse])
def get_prospects_by_advisor(codigo_asesor: int, db: Session = Depends(get_db)):
    return db.query(Prospect).filter(Prospect.codigo_asesor == codigo_asesor).all()
