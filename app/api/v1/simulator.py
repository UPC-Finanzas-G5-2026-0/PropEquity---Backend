from fastapi import APIRouter, HTTPException
from ...schemas.simulation import SimulationInput, SimulationResult
from ...services.finance import get_monthly_schedule


router = APIRouter()


@router.post("/calculate", response_model=SimulationResult)
def calculate_loan(payload: SimulationInput):
    try:
        return get_monthly_schedule(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))