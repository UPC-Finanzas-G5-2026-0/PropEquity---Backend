# test_integration.py
import sys
import os

# 1. Obtener la ruta absoluta del directorio actual (tests/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Obtener la ruta del directorio PADRE (PropEquity-backend/)
parent_dir = os.path.dirname(current_dir)

# 3. Agregar el directorio padre al path de Python
sys.path.append(parent_dir)

# Importamos tus Schemas y la Lógica Financiera
from app.schemas.simulation import SimulationInput, TipoTasa, TipoGracia, FrecuenciaCapitalizacion
from app.services.finance import get_monthly_schedule

def probar_metodo_frances():
    print("--- INICIANDO PRUEBA DE INTEGRACIÓN: MÉTODO FRANCÉS ---")

    # 1. Definir datos de prueba (Como si vinieran del Frontend/Swagger)
    # Caso: Préstamo de 200,000 con Tasa Efectiva, a 20 años (240 meses)
    datos_entrada = SimulationInput(
        precio_venta=250000.00,
        cuota_inicial=50000.00, # Préstamo neto: 200,000
        bono_bbp=0.0,
        
        tipo_tasa=TipoTasa.EFECTIVA,
        tasa_valor=12.5, # 12.5% TEA
        
        plazo_meses=240, # 20 años
        
        seguro_desgravamen_porc=0.028, # 0.028% mensual
        seguro_inmueble_anual=0.30,    # 0.30% anual
        
        tipo_gracia=TipoGracia.NINGUNO,
        meses_gracia=0
    )

    print(f"Datos: Préstamo S/ {datos_entrada.precio_venta - datos_entrada.cuota_inicial}")
    print(f"Plazo: {datos_entrada.plazo_meses} meses")
    print(f"Tasa: {datos_entrada.tasa_valor}% {datos_entrada.tipo_tasa}")

    try:
        # 2. Llamar a la función que integra la lógica (finance.py)
        resultado = get_monthly_schedule(datos_entrada)

        # 3. Validar resultados básicos
        print("\n--- RESULTADOS ---")
        print(f"TEM Calculada: {resultado.input_resumen['tem_calculada']}%")
        print(f"Cuota Mensual (aprox): S/ {resultado.cronograma[1].cuota_total}")
        print(f"Total Intereses: S/ {resultado.indicadores['total_intereses']}")
        print(f"TCEA: {resultado.indicadores['tcea']}%")

        # 4. Verificación de saldo cero al final
        ultimo_pago = resultado.cronograma[-1]
        print(f"\nSaldo Final (Mes {ultimo_pago.numero_cuota}): {ultimo_pago.saldo_final}")
        
        if ultimo_pago.saldo_final == 0:
            print("✅ ÉXITO: El préstamo se pagó completamente.")
        else:
            print("⚠️ ADVERTENCIA: Quedó un saldo pendiente (revisar redondeo).")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    probar_metodo_frances()