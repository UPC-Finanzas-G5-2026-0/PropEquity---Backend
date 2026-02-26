import numpy_financial as npf

def get_monthly_schedule(precio_venta, data):
    # El capital es Precio - Cuota Inicial + Seguro (si aplica) - Bono
    # Pero el bono BBP suele reducir el monto del préstamo o la cuota.
    # Siguiendo lógica estándar: 
    monto_prestamo = float(precio_venta) - float(data.cuota_inicial) - float(data.bono_bbp) + float(data.seguro_desgravamen)
    
    # Conversión de Tasa
    if data.codigo_tipo_tasa == 1: # Nominal
        # Tasa efectiva mensual desde nominal con capitalización (asumiendo mensual por defecto)
        tem = (float(data.tasa_anual) / 100) / 12
    else: # Efectiva
        # Tasa efectiva mensual desde TEA
        tem = (1 + (float(data.tasa_anual) / 100))**(1/12) - 1
        
    saldo = monto_prestamo
    cronograma = []
    
    for m in range(1, data.plazo_meses + 1):
        interes = saldo * tem
        
        if m <= data.meses_gracia:
            if data.codigo_tipo_gracia == 3: # Total
                cuota, amort = 0, 0
                saldo += interes # Capitalización de intereses
            elif data.codigo_tipo_gracia == 2: # Parcial
                cuota, amort = interes, 0
            else: # Ninguno
                meses_pago = data.plazo_meses
                cuota = npf.pmt(tem, meses_pago, -monto_prestamo)
                amort = cuota - interes
                saldo -= amort
        else:
            # Después de la gracia, recalculamos cuota sobre el saldo actual
            meses_restantes = data.plazo_meses - data.meses_gracia
            cuota = npf.pmt(tem, meses_restantes, -saldo)
            amort = cuota - interes
            saldo -= amort
            
        cronograma.append({
            "mes": m, 
            "cuota": round(cuota, 2), 
            "interes": round(interes, 2),
            "amortizacion": round(amort, 2), 
            "saldo": round(max(0, saldo), 2)
        })
    
    flujos = [-monto_prestamo] + [c['cuota'] for c in cronograma]
    return {
        "cronograma": cronograma,
        "van": round(npf.npv(tem, flujos), 2),
        "tir": round(npf.irr(flujos) * 100, 4) if any(flujos) else 0.0 # TIR Mensual (%)
    }
