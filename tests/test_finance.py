from app.services.finance import get_monthly_schedule
from app.schemas.simulation import SimulationInput

def test_calculo_frances_basico():
    data = SimulationInput(
        precio_venta=250000,
        cuota_inicial=25000,
        tea=0.10,
        plazo_meses=120,
        tipo_gracia="NINGUNO",
        meses_gracia=0
    )
    resultado = get_monthly_schedule(data)
    # El saldo final del último mes debe ser 0
    assert resultado["cronograma"][-1]["saldo"] == 0
    print("Prueba de amortización exitosa")