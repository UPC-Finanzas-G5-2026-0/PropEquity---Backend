import requests
from decimal import Decimal

# Configuración
BASE_URL = "https://propequity-backend.onrender.com/api/v1"

def test_nominal_bimestral_calc():
    # Parámetros del test
    tna = 12.0  # 12% Nominal Anual
    capitalizacion = "Bimestral"
    
    # 1. Obtener una unidad válida
    units = requests.get(f"{BASE_URL}/units/").json()
    if not units:
        print("❌ No hay unidades disponibles para testear.")
        return
    unidad = units[0]
    codigo_unidad = unidad['codigo_unidad']
    precio = unity_price = unidad['precio_venta']
    
    # 2. Preparar payload de simulación
    payload = {
        "codigo_unidad": codigo_unidad,
        "cuota_inicial": 10.0,
        "tipo_tasa": "Nominal",
        "tasa_anual": tna,
        "capitalizacion": capitalizacion,
        "plazo_meses": 20,
        "seguro_desgravamen": 0.028,
        "tipo_gracia": "Ninguno",
        "meses_gracia": 0,
        "tipo_bbp": "Ninguno"
    }
    
    print(f"--- Test de Tasa Nominal Bimestral ---")
    print(f"TNA enviada: {tna}%")
    print(f"Capitalización: {capitalizacion}")
    
    # 3. Llamar al simulador
    # No necesitamos token si el endpoint lo permite o usamos uno genérico
    response = requests.post(f"{BASE_URL}/simulator/?save=false", json=payload)
    
    if response.status_code != 200:
        print(f"❌ Error en la API: {response.text}")
        return

    res_data = response.json()
    # Los detalles del cronograma contienen la TEA y TEM calculada
    # La cuota 1 suele tener estos valores
    primera_cuota = res_data['cronograma'][1]
    tea_calc = float(primera_cuota['tea'])
    tem_calc = float(primera_cuota['tem'])
    
    # 4. Verificación Matemática Manual
    # TEA = (1 + i_nom/m)^m - 1
    # m = 12 / 2 = 6 (bimestres)
    m = 6
    tna_dec = tna / 100
    expected_tea = ((1 + tna_dec / m) ** m - 1) * 100
    
    # TEM = (1 + TEA)^(1/12) - 1
    expected_tem = ((1 + expected_tea/100) ** (1/12) - 1) * 100
    
    print(f"\nResultados del Sistema:")
    print(f"TEA: {tea_calc:.6f}%")
    print(f"TEM: {tem_calc:.6f}%")
    
    print(f"\nVerificación Matemática:")
    print(f"TEA Esperada: {expected_tea:.6f}%")
    print(f"TEM Esperada: {expected_tem:.6f}%")
    
    # Comparación (con margen de error por decimales)
    if abs(tea_calc - expected_tea) < 0.0001 and abs(tem_calc - expected_tem) < 0.0001:
        print(f"\n✅ EL TEST PASÓ: Los cálculos nominales coinciden perfectamente.")
    else:
        print(f"\n❌ EL TEST FALLÓ: Hay una discrepancia en los cálculos.")

if __name__ == "__main__":
    test_nominal_bimestral_calc()
