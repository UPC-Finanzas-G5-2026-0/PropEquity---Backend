from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

# 1. Importaciones Absolutas (Para evitar errores)
from app.database import get_db
from app.models import User
from app.core.security import get_current_user
from app.schemas.simulation import SimulationInput, SimulationResult

# Asumimos que la lógica de negocio está en 'services.finance'
from app.services.finance import get_monthly_schedule

router = APIRouter()

@router.post("/calculate", response_model=SimulationResult)
def calculate_loan(
    payload: SimulationInput, 
    current_user: User = Depends(get_current_user), # 2. Ruta Protegida con JWT
    db: Session = Depends(get_db)
):
    """
    Endpoint principal para el Simulador.
    Recibe la configuración compleja (Tasas, Seguros, Gracia) y devuelve el cronograma + KPIs.
    """
    try:
        # Aquí llamamos al servicio que orquesta la matemática
        result = get_monthly_schedule(payload)
        return result
    except ValueError as ve:
        # Errores de validación de negocio (ej: Tasa negativa)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Errores inesperados del servidor
        print(f"Error en simulación: {e}") # Log para ti en consola
        raise HTTPException(status_code=500, detail="Error interno al procesar la simulación")

# Nota: El endpoint '/french-schedule' que tenías puede quedar como 
# una herramienta de prueba interna, pero el frontend debería usar '/calculate'.