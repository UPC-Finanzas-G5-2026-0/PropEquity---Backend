from decimal import Decimal, ROUND_HALF_UP
import numpy_financial as npf


def _round2(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def get_monthly_schedule(data):
    capital = data.precio_venta - data.cuota_inicial
    tem = (1 + data.tea)**(1/12) - 1
    saldo = capital
    cronograma = []
    meses_pago = data.plazo_meses - (data.meses_gracia if data.tipo_gracia != "NINGUNO" else 0)
    cuota_base = None
    cuotas_emitidas = 0
    
    for m in range(1, data.plazo_meses + 1):
        interes = saldo * tem
        
        if m <= data.meses_gracia:
            if data.tipo_gracia == "TOTAL":
                cuota, amort = 0, 0
                saldo += interes # Capitalización
            else: # PARCIAL
                cuota, amort = interes, 0
        else:
            # Método Francés: cuotas constantes después de gracia
            if cuota_base is None:
                cuota_base = npf.pmt(tem, meses_pago, -saldo)

            cuotas_emitidas += 1
            if cuotas_emitidas == meses_pago:
                amort = saldo
                cuota = interes + amort
                saldo = 0
            else:
                cuota = cuota_base
                amort = cuota - interes
                saldo -= amort
            
        cronograma.append({
            "mes": m,
            "cuota": _round2(cuota),
            "interes": _round2(interes),
            "amortizacion": _round2(amort),
            "saldo": 0.0 if saldo == 0 else _round2(max(0, saldo))
        })
    
    flujos = [-capital] + [c['cuota'] for c in cronograma]
    return {
        "cronograma": cronograma,
        "van": _round2(npf.npv(tem, flujos)),
        "tir": _round2(npf.irr(flujos) * 100) # TIR Mensual (%)
    }
