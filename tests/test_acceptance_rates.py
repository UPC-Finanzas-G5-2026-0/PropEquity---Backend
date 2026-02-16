import sys
import os

# 1. Obtener la ruta donde está este archivo (carpeta tests)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Obtener la ruta PADRE (carpeta raíz del proyecto)
parent_dir = os.path.dirname(current_dir)

# 3. Agregar la raíz al sistema para poder importar 'app'
sys.path.append(parent_dir)

# Ahora sí, importar...
from pydantic import ValidationError
from app.schemas.simulation import SimulationInput, TipoTasa, FrecuenciaCapitalizacion


def test_criterios_aceptacion():
    print("--- INICIANDO PRUEBA DE ACEPTACIÓN: TASAS ---")

    # CASO 1: Usuario elige Tasa NOMINAL pero olvida la Capitalización
    # Resultado esperado: ERROR (El sistema debe impedirlo)
    print("\n1. Probando TNA sin Capitalización (Debe fallar)...")
    try:
        SimulationInput(
            precio_venta=100000,
            cuota_inicial=10000,
            tipo_tasa=TipoTasa.NOMINAL, # <--- ES NOMINAL
            tasa_valor=10.5,
            capitalization=None,        # <--- PERO NO TIENE CAPITALIZACIÓN
            plazo_meses=120,
            seguro_desgravamen_porc=0.05,
            seguro_inmueble_anual=0.25
        )
        print("❌ FALLO: El sistema permitió una TNA sin capitalización (Mal).")
    except ValueError as e:
        print(f"✅ ÉXITO: El sistema bloqueó el error: {e}")

    # CASO 2: Usuario elige Tasa NOMINAL CON Capitalización Diaria
    # Resultado esperado: ÉXITO
    print("\n2. Probando TNA con Capitalización Diaria (Debe pasar)...")
    try:
        input_valido = SimulationInput(
            precio_venta=100000,
            cuota_inicial=10000,
            tipo_tasa=TipoTasa.NOMINAL, # <--- ES NOMINAL
            tasa_valor=10.5,
            capitalization=FrecuenciaCapitalizacion.DIARIA, # <--- TIENE CAPITALIZACIÓN
            plazo_meses=120,
            seguro_desgravamen_porc=0.05,
            seguro_inmueble_anual=0.25
        )
        print("✅ ÉXITO: El sistema aceptó la configuración válida.")
    except Exception as e:
        print(f"❌ FALLO: Hubo un error inesperado: {e}")

if __name__ == "__main__":
    test_criterios_aceptacion()