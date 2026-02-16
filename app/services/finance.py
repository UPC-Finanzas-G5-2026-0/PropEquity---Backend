import math
import numpy_financial as npf # Asegúrate de tenerlo: pip install numpy-financial
from decimal import Decimal, ROUND_HALF_UP

# Importamos los esquemas y Enums que definimos antes
from app.schemas.simulation import (
    SimulationInput, 
    SimulationResult, 
    PaymentDetail, 
    TipoTasa, 
    TipoGracia, 
    FrecuenciaCapitalizacion
)

def _round2(value: float) -> float:
    """Función auxiliar para redondeo financiero a 2 decimales"""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def get_monthly_schedule(data: SimulationInput) -> SimulationResult:
    # --- 1. DATOS INICIALES ---
    precio_venta = data.precio_venta
    monto_prestamo = precio_venta - data.cuota_inicial - data.bono_bbp
    
    # --- 2. CONVERSIÓN DE TASAS A TEM (Tasa Efectiva Mensual) ---
    tasa_anual = data.tasa_valor / 100
    tem = 0.0

    if data.tipo_tasa == TipoTasa.NOMINAL:
        # Lógica para Tasa Nominal (TNA)
        # Asumimos año base 360 días para productos financieros
        m = 0 
        if data.capitalizacion == FrecuenciaCapitalizacion.DIARIA:
            m = 360
        elif data.capitalizacion == FrecuenciaCapitalizacion.MENSUAL:
            m = 12
        elif data.capitalizacion == FrecuenciaCapitalizacion.SEMESTRAL:
            m = 2
        else:
            # Default a diaria si no se especifica
            m = 360 
            
        # Fórmula: TNA -> TEA = (1 + TNA/m)^m - 1
        tea = ((1 + tasa_anual / m) ** m) - 1
        # Fórmula: TEA -> TEM = (1 + TEA)^(1/12) - 1
        tem = ((1 + tea) ** (1/12)) - 1
        
    else:
        # Lógica para Tasa Efectiva (TEA) directa
        # Fórmula: TEA -> TEM
        tem = ((1 + tasa_anual) ** (1/12)) - 1

    # --- 3. CÁLCULO DE SEGUROS ---
    # Seguro Desgravamen: % mensual sobre el SALDO DEUDOR (o saldo insoluto)
    tasa_desgravamen_mensual = data.seguro_desgravamen_porc / 100
    
    # Seguro Inmueble: % anual sobre el PRECIO DE VENTA (dividido entre 12)
    monto_seguro_inmueble = (precio_venta * (data.seguro_inmueble_anual / 100)) / 12

    # --- 4. GENERACIÓN DEL CRONOGRAMA ---
    saldo_insoluto = monto_prestamo
    cronograma = []
    
    # Determinar meses de gracia
    meses_gracia = data.meses_gracia if data.tipo_gracia != TipoGracia.NINGUNO else 0
    plazo_total = data.plazo_meses
    
    # Variables para cálculo de cuota francesa (PMT)
    # El plazo restante para amortizar capital
    plazo_pago = plazo_total - meses_gracia 

    for cuota_n in range(1, plazo_total + 1):
        # A. Cálculo de Interés del periodo
        interes = saldo_insoluto * tem
        
        # B. Cálculo de Seguro Desgravamen del periodo
        seguro_desgravamen = saldo_insoluto * tasa_desgravamen_mensual
        
        amortizacion = 0.0
        cuota_mensual_base = 0.0 # Sin seguros
        
        # --- LÓGICA DE PERIODOS ---
        if cuota_n <= meses_gracia:
            # Estamos en Periodo de Gracia
            if data.tipo_gracia == TipoGracia.TOTAL:
                # Gracia Total: No se paga nada. El interés se suma al capital (Capitalización)
                amortizacion = 0.0
                cuota_mensual_base = 0.0 # El cliente paga 0
                saldo_insoluto += interes # El interés se vuelve nueva deuda
                # Nota: En gracia total, el seguro se suele pagar o capitalizar. 
                # Para simplificar este modelo, asumiremos que los seguros SE PAGAN.
                cuota_total_cliente = seguro_desgravamen + monto_seguro_inmueble
                
            else: # TipoGracia.PARCIAL
                # Gracia Parcial: Se paga interés, pero no se amortiza capital
                amortizacion = 0.0
                cuota_mensual_base = interes
                # El saldo se mantiene igual
                cuota_total_cliente = cuota_mensual_base + seguro_desgravamen + monto_seguro_inmueble
        
        else:
            # Estamos en Periodo de Amortización (Método Francés)
            # Recalculamos la cuota fija sobre el saldo actual y el plazo restante
            # Esto es vital porque si hubo Gracia Total, el saldo aumentó.
            
            # Plazo restante real
            meses_restantes = plazo_total - cuota_n + 1
            
            if saldo_insoluto > 0:
                # Fórmula PMT: R = P * [ i(1+i)^n ] / [ (1+i)^n - 1 ]
                factor = (1 + tem) ** meses_restantes
                cuota_francesa = saldo_insoluto * ((tem * factor) / (factor - 1))
            else:
                cuota_francesa = 0

            cuota_mensual_base = cuota_francesa
            
            # Desgloce
            interes_cuota = interes # Ya calculado arriba
            amortizacion = cuota_mensual_base - interes_cuota
            
            # Ajuste final por redondeo en la última cuota
            if cuota_n == plazo_total:
                amortizacion = saldo_insoluto
                cuota_mensual_base = amortizacion + interes_cuota
            
            cuota_total_cliente = cuota_mensual_base + seguro_desgravamen + monto_seguro_inmueble
            
            # Actualizar Saldo
            saldo_insoluto -= amortizacion
            if saldo_insoluto < 0: saldo_insoluto = 0

        # --- GUARDAR DETALLE ---
        detalle = PaymentDetail(
            numero_cuota=cuota_n,
            saldo_inicial=_round2(saldo_insoluto + amortizacion if cuota_n > meses_gracia or data.tipo_gracia == TipoGracia.PARCIAL else saldo_insoluto - interes), # Reconstrucción visual aproximada
            amortizacion=_round2(amortizacion),
            interes=_round2(interes),
            seguro_desgravamen=_round2(seguro_desgravamen),
            seguro_inmueble=_round2(monto_seguro_inmueble),
            cuota_total=_round2(cuota_total_cliente),
            saldo_final=_round2(saldo_insoluto),
            flujo_caja=_round2(cuota_total_cliente) # Flujo para el cálculo de indicadores
        )
        cronograma.append(detalle)

    # --- 5. CÁLCULO DE INDICADORES (KPIs) ---
    
    # Flujo de caja para VAN/TIR:
    # Momento 0: -Monto Prestamo (Salida de dinero del banco/Inversión)
    # Momento 1..n: Cuotas Totales (Entrada de dinero)
    
    # OJO: Para el cliente (TCEA), el flujo inicial es lo que recibe (Prestamo) menos gastos iniciales.
    # Para simplificar, usaremos el flujo del préstamo neto.
    
    flujos = [-monto_prestamo] + [c.flujo_caja for c in cronograma]
    
    van = npf.npv(tem, flujos)
    tir_mensual = npf.irr(flujos) 
    
    # TCEA (Tasa de Costo Efectivo Anual)
    # Fórmula: (1 + TIR_Mensual)^12 - 1
    tcea = 0.0
    if tir_mensual is not None and not math.isnan(tir_mensual):
        tcea = ((1 + tir_mensual) ** 12) - 1

    return SimulationResult(
        input_resumen={
            "monto_prestamo": _round2(monto_prestamo),
            "tem_calculada": _round2(tem * 100) # En porcentaje
        },
        cronograma=cronograma,
        indicadores={
            "van": _round2(van),
            "tir": _round2((tir_mensual or 0) * 100), # TIR Mensual %
            "tcea": _round2(tcea * 100), # TCEA Anual %
            "total_intereses": _round2(sum(c.interes for c in cronograma))
        }
    )