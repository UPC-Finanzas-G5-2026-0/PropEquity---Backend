from fastapi import APIRouter, HTTPException
from ...schemas.simulation import SimulationInput, SimulationResult
from ...schemas.amortization import FrenchScheduleInput, FrenchScheduleResult
from ...services.finance import get_monthly_schedule
from ...services.amortization import generate_french_schedule


router = APIRouter()


@router.post("/calculate", response_model=SimulationResult)
def calculate_loan(payload: SimulationInput):
    try:
        return get_monthly_schedule(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/french-schedule", response_model=FrenchScheduleResult)
def calculate_french_schedule(payload: FrenchScheduleInput):
    try:
        cronograma = generate_french_schedule(
            principal=payload.principal,
            rate=payload.rate,
            rate_type=payload.rate_type,
            n_periods=payload.n_periods,
            payment_period=payload.payment_period,
            capitalization=payload.capitalization,
            rate_period=payload.rate_period,
        )
        return {"cronograma": cronograma}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
