import numpy_financial as npf

def get_monthly_schedule(data):
    capital = data.precio_venta - data.cuota_inicial
    tem = (1 + data.tea)**(1/12) - 1
    saldo = capital
    cronograma = []
    
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
            meses_pago = data.plazo_meses - (data.meses_gracia if data.tipo_gracia != "NINGUNO" else 0)
            cuota = npf.pmt(tem, meses_pago, -saldo)
            amort = cuota - interes
            saldo -= amort
            
        cronograma.append({
            "mes": m, "cuota": round(cuota, 2), "interes": round(interes, 2),
            "amortizacion": round(amort, 2), "saldo": round(max(0, saldo), 2)
        })
    
    flujos = [-capital] + [c['cuota'] for c in cronograma]
    return {
        "cronograma": cronograma,
        "van": round(npf.npv(tem, flujos), 2),
        "tir": round(npf.irr(flujos) * 100, 2) # TIR Mensual (%)
    }