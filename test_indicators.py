
import sys
import os
from decimal import Decimal
import numpy_financial as npf
from datetime import date

# Añadir el directorio raíz al path para importar la app
sys.path.append(os.getcwd())

def test_profitability_indicators():
    print("=== TEST DE INDICADORES DE RENTABILIDAD ===")
    
    # Datos de entrada similares al Excel del usuario
    # Monto Préstamo: 141,100.00
    # TEA: 13.25%
    # Plazo: 240 meses
    # Gastos Periódicos: 100 + 200 + 200 = 500
    # Gastos Iniciales: Vamos a poner 0 para aislar el efecto de los periódicos primero
    
    monto_financiar = Decimal("141100.00")
    gastos_iniciales = Decimal("0.00")
    tea_anual = Decimal("0.1325")
    n_total = 240
    seguro_tasa = Decimal("0.0004") # Aproximado para que de 56.44
    com_per = Decimal("0.00")
    portes = Decimal("0.00")
    gast_adm = Decimal("0.00")

    gastos_periodicos = Decimal("0.00")
    
    # 1. Tasa de Descuento (30/360)
    TASA_DESCUENTO_ANUAL = Decimal("0.08")
    tasa_descuento_mensual = (1 + TASA_DESCUENTO_ANUAL) ** (Decimal("30") / Decimal("360")) - 1
    print(f"Tasa Descuento Mensual (8% COK): {tasa_descuento_mensual*100:.5f}% (Excel: 0.64340%)")
    
    # 2. Calcular Cuota Base (Francés)
    tem = (1 + tea_anual) ** (Decimal("1") / Decimal("12")) - 1
    factor = (tem * (1 + tem) ** n_total) / ((1 + tem) ** n_total - 1)
    cuota_base = monto_financiar * factor
    print(f"Cuota Base (Capital+Int): S/ {cuota_base:.2f}")
    
    # 3. Flujos de Caja
    # Mes 0: Préstamo - Gastos Iniciales
    flujo_0 = float(monto_financiar - gastos_iniciales)
    
    # Cuota con seguro pero sin gastos periódicos
    seguro_aprox = monto_financiar * seguro_tasa
    cuota_total = cuota_base + seguro_aprox
    print(f"Seguro aprox: S/ {seguro_aprox:.2f}")
    print(f"Cuota Total (Flujo): S/ {cuota_total:.2f}")
    
    flujos = [flujo_0] + [-float(cuota_total)] * n_total

    
    # 4. Cálculo de Indicadores
    tir = npf.irr(flujos)
    tcea = ((1 + tir) ** 12) - 1
    van = npf.npv(float(tasa_descuento_mensual), flujos)
    
    print("-" * 40)
    print(f"RESULTADOS CALCULADOS:")
    print(f"TIR Mensual: {tir*100:.5f}%")
    print(f"TCEA Anual:  {tcea*100:.5f}%")
    print(f"VAN:         S/ {van:,.2f}")
    print("-" * 40)
    
    # Verificación contra Excel (Valores aproximados por redondeos de cuota)
    # En el excel: TIR 1.48019%, TCEA 19.28212%, VAN -121,591.26
    print("VERIFICACIÓN:")
    if abs(Decimal(str(tir*100)) - Decimal("1.48019")) < 0.01:
        print("✅ TIR coincidente")
    else:
        print("❌ TIR diferente")
        
    if abs(Decimal(str(tcea*100)) - Decimal("19.28212")) < 0.05:
        print("✅ TCEA coincidente")
    else:
        print("❌ TCEA diferente")

if __name__ == "__main__":
    test_profitability_indicators()
