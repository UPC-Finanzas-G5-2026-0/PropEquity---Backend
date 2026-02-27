from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import numpy_financial as npf
import pandas as pd
import io
from typing import List
from app.database import get_db
from app.models import Unit, Simulation, SimulationResult, SimulationDetail, Client, Advisor, Prospect, BonoBBP, CreditoIFI, User, ModalidadVivienda, TipoVenta
from app.schemas.simulation import SimulationCreate, SimulationResponse
from app.core.security import get_current_user
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

router = APIRouter()

def d2(val):
    if isinstance(val, (float, int)):
        val = Decimal(str(val))
    return val.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

def get_bono_info(db: Session, precio_venta: Decimal, tipo_bbp: str, modalidad: str) -> dict:
    """Calcula rango, bono base e integrador según tablas técnicas."""
    if modalidad == "Mejoramiento" or precio_venta > Decimal("488800.00") or tipo_bbp == "Ninguno":
        return {"rango": "SinBBP", "base": Decimal("0.00"), "integrador": Decimal("0.00")}

    bono_row = db.query(BonoBBP).filter(
        BonoBBP.valor_vivienda_min <= precio_venta,
        BonoBBP.valor_vivienda_max >= precio_venta
    ).first()

    if not bono_row or bono_row.rango == "R5":
        return {"rango": (bono_row.rango if bono_row else "SinBBP"), "base": Decimal("0.00"), "integrador": Decimal("0.00")}

    mapping = {
        "Tradicional": bono_row.bono_tradicional,
        "Sostenible": bono_row.bono_sostenible,
        "Integrador Tradicional": bono_row.bono_tradicional,
        "Integrador Sostenible": bono_row.bono_sostenible,
    }
    
    base = Decimal(str(mapping.get(tipo_bbp, 0)))
    integrador = Decimal("3600.00") if "Integrador" in tipo_bbp else Decimal("0.00")
    
    return {"rango": bono_row.rango, "base": base, "integrador": integrador}


def get_capitalizacion_factor(capitalizacion: str) -> int:
    """Retorna el número de meses de capitalización para tasa nominal."""
    return {"Mensual": 1, "Bimestral": 2, "Trimestral": 3}.get(capitalizacion, 1)


@router.get("/ifis-disponibles")
def get_ifis_disponibles(
    monto: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Devuelve las IFIs disponibles para un monto de financiamiento dado.
    Incluye rango de TEA y tasas de seguro por tipo (individual/mancomunado).
    """
    from decimal import Decimal
    monto_dec = Decimal(str(monto))
    results = db.query(CreditoIFI).filter(
        CreditoIFI.monto_min <= monto_dec,
        (CreditoIFI.monto_max >= monto_dec) | (CreditoIFI.monto_max == None)
    ).all()

    return [
        {
            "nombre_ifi": r.nombre_ifi,
            "plazo_min_anios": r.plazo_min_anios,
            "plazo_max_anios": r.plazo_max_anios,
            "tea_min": float(r.tea_min),
            "tea_max": float(r.tea_max),
            "seguro_individual": float(r.seguro_individual),
            "seguro_mancomunado": float(r.seguro_mancomunado),
        }
        for r in results
    ]


@router.post("/", response_model=SimulationResponse)
def run_simulation(
    payload: SimulationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validar unidad y obtener modalidad
    unit = db.query(Unit).filter(Unit.codigo_unidad == payload.codigo_unidad).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")

    modalidad = "Compra"
    if unit.codigo_modalidad:
        mod = db.query(ModalidadVivienda).filter(ModalidadVivienda.codigo_modalidad == unit.codigo_modalidad).first()
        modalidad = mod.nombre_modalidad if mod else "Compra"

    role = current_user.rol_rel.tipo_rol
    # 2. Asignar identificadores por rol
    if role == "Cliente":
        if payload.codigo_cliente and payload.codigo_cliente != current_user.codigo_usuario:
            raise HTTPException(status_code=403, detail="No puedes crear simulaciones en nombre de otro cliente.")
        payload.codigo_cliente = current_user.codigo_usuario
        payload.codigo_asesor = None
        payload.codigo_prospecto = None
    elif role == "Asesor":
        payload.codigo_asesor = current_user.codigo_usuario
        payload.codigo_cliente = None
        if payload.codigo_prospecto is None:
            raise HTTPException(status_code=400, detail="El asesor debe indicar el codigo_prospecto para simular.")

    # ═══ VALIDACIONES MOVIDAS DEL SCHEMA PARA EVITAR ERRORES 500 ═══
    
    # Validar tipo BBP
    TIPOS_BBP = ["Ninguno", "Tradicional", "Sostenible", "Integrador Tradicional", "Integrador Sostenible"]
    if payload.tipo_bbp not in TIPOS_BBP:
        raise HTTPException(status_code=422, detail=f"tipo_bbp debe ser uno de: {TIPOS_BBP}")
    
    # Validar BBP Integrador
    CATEGORIAS_INTEGRADOR = ["Menores ingresos", "Adulto mayor", "Discapacidad", "Desplazado", "Migrante retornado"]
    if "Integrador" in payload.tipo_bbp:
        if not payload.categoria_integrador:
            raise HTTPException(status_code=422, detail="categoria_integrador es requerida cuando tipo_bbp es Integrador.")
        if payload.categoria_integrador not in CATEGORIAS_INTEGRADOR:
            raise HTTPException(status_code=422, detail=f"categoria_integrador debe ser una de: {CATEGORIAS_INTEGRADOR}")
        # ingreso_maximo solo aplica si categoria = "Menores ingresos"
        if payload.categoria_integrador == "Menores ingresos":
            if payload.ingreso_maximo_integrador is None:
                raise HTTPException(status_code=422, detail="ingreso_maximo_integrador es requerido para 'Menores ingresos'.")
            if payload.ingreso_maximo_integrador > 4746.00:
                raise HTTPException(status_code=422, detail="ingreso_maximo_integrador no puede superar S/ 4,746.00")
    else:
        # Si no es integrador, limpiar campos integrador
        payload.categoria_integrador = None
        payload.ingreso_maximo_integrador = None

    # Validar período de gracia general
    if payload.meses_gracia >= payload.plazo_meses:
        raise HTTPException(status_code=422, detail="meses_gracia debe ser menor que plazo_meses.")

    # Validar período de gracia TOTAL (máximo 6 meses)
    if payload.tipo_gracia == "Total" and payload.meses_gracia > 6:
        raise HTTPException(status_code=422, detail="El periodo de gracia total no puede superar los 6 meses.")

    # ═══ FIN VALIDACIONES MOVIDAS ═══

    # 3. Conversión de Moneda y Cálculo de BBP (R1-R5)
    pv = Decimal(str(unit.precio_venta))
    tipo_cambio = Decimal(str(payload.tipo_cambio))

    # El BBP siempre se valida en Soles (PEN) según reglamento
    pv_pen = pv
    if unit.moneda_rel.simbolo_moneda == "USD":
        pv_pen = pv * tipo_cambio

    bono_info = get_bono_info(db, pv_pen, payload.tipo_bbp, modalidad)
    rango = bono_info["rango"]
    
    # Los bonos en la DB están en PEN. Si la unidad es USD, convertimos el bono a USD.
    bono_base = bono_info["base"]
    bono_integrador = bono_info["integrador"]
    if unit.moneda_rel.simbolo_moneda == "USD":
        bono_base = (bono_base / tipo_cambio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        bono_integrador = (bono_integrador / tipo_cambio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    bono_total = bono_base + bono_integrador

    # Validaciones exclusividad BBP
    if payload.tipo_bbp != "Ninguno" and not payload.ifi_seleccionada:
        raise HTTPException(status_code=400, detail="El BBP solo aplica con el Crédito MiVivienda a través de una IFI.")

    # Vivienda Sostenible vs Tradicional: Exclusividad
    if unit.es_sostenible:
        if payload.tipo_bbp in ["Tradicional", "Integrador Tradicional"]:
            raise HTTPException(status_code=400, detail="Vivienda Sostenible solo acepta bonos Sostenibles.")
    else:
        if payload.tipo_bbp in ["Sostenible", "Integrador Sostenible"]:
            raise HTTPException(status_code=400, detail="Vivienda Tradicional solo acepta bonos Tradicionales.")

    # 🚨 RESTRICCIÓN NCMV: Solo Primera Venta 🚨
    if payload.tipo_bbp != "Ninguno":
        tipo_v = db.query(TipoVenta).filter(TipoVenta.codigo_tipo_venta == unit.codigo_tipo_venta).first()
        if tipo_v and tipo_v.nombre_tipo_venta == "Segunda venta":
            raise HTTPException(
                status_code=400,
                detail="El Bono de Buen Pagador (BBP) solo aplica para unidades de Primera Venta (Nuevas). Las viviendas de segunda venta no califican."
            )

    # 🚨 RESTRICCIÓN MIVIVIENDA: Propiedad y Apoyo Estatal Previo 🚨
    if payload.tipo_bbp != "Ninguno":
        # Obtener entidad para validar (Cliente o Prospecto)
        entity = None
        if role == "Cliente":
            entity = db.query(Client).filter(Client.codigo_cliente == current_user.codigo_usuario).first()
        elif role == "Asesor" and payload.codigo_prospecto:
            entity = db.query(Prospect).filter(Prospect.codigo_prospecto == payload.codigo_prospecto).first()
        
        if entity:
            if entity.es_propietario_vivienda or entity.hijos_menores_propietarios:
                raise HTTPException(
                    status_code=400,
                    detail="El Crédito MiVivienda NO aplica si el titular, cónyuge o hijos menores son propietarios de otra vivienda."
                )
            if entity.recibio_apoyo_estatal:
                raise HTTPException(
                    status_code=400,
                    detail="El Crédito MiVivienda y sus bonos NO aplican si el beneficiario ya recibió apoyo habitacional del Estado (Techo Propio, FMV, etc.)."
                )
            if entity.cantidad_creditos_fmv >= 2:
                raise HTTPException(
                    status_code=400,
                    detail="El beneficiario ha alcanzado el límite máximo de 2 créditos MiVivienda permitidos por historial."
                )
            if entity.tiene_credito_fmv_activo:
                raise HTTPException(
                    status_code=400,
                    detail="El beneficiario tiene un Crédito MiVivienda ACTIVO. No puede solicitar otro hasta cancelar el actual."
                )

    # 4. Gastos cierre y Cuota Inicial
    gastos_cierre = Decimal(str(payload.gastos_cierre))
    cuota_inicial = Decimal(str(payload.cuota_inicial))

    # 🚨 RESTRICCIÓN NCMV: Cuota Inicial Mínima 🚨
    # 10% para Compra, 7.5% para Construcción/Mejoramiento
    porcentaje_inicial = (cuota_inicial / pv) * 100
    if modalidad in ["Construccion", "Mejoramiento"]:
        min_porcentaje = Decimal("7.5")
    else:
        min_porcentaje = Decimal("10.0")

    if porcentaje_inicial < min_porcentaje:
        raise HTTPException(
            status_code=400,
            detail=f"La cuota inicial ({float(porcentaje_inicial):.1f}%) es insuficiente. Para modalidad '{modalidad}' se requiere un mínimo del {float(min_porcentaje)}%."
        )

    # 5. Cálculo del Préstamo (Monto a Financiar)
    precio_neto = pv - bono_total
    monto_financiar = (precio_neto - cuota_inicial) + gastos_cierre

    # Restricción LTV 90%
    if modalidad not in ["Construccion", "Mejoramiento"]:
        max_financiar = pv * Decimal("0.90")
        if monto_financiar > max_financiar:
            raise HTTPException(status_code=400, detail=f"Financiamiento excede el 90% (S/ {float(max_financiar):,.2f}).")

    if monto_financiar <= 0:
        raise HTTPException(status_code=400, detail="El monto a financiar debe ser mayor a 0.")

    # ─── MODO IFI vs MODO MANUAL (Precarga y Bloqueos) ─────────────────────────
    if payload.ifi_seleccionada:
        # ── MODO IFI ──
        ifi_row = db.query(CreditoIFI).filter(
            CreditoIFI.nombre_ifi == payload.ifi_seleccionada,
            CreditoIFI.monto_min <= monto_financiar,
            (CreditoIFI.monto_max >= monto_financiar) | (CreditoIFI.monto_max == None)
        ).first()

        if not ifi_row:
            raise HTTPException(
                status_code=400,
                detail=f"Monto de S/ {float(monto_financiar):,.2f} fuera de rango para {payload.ifi_seleccionada}."
            )

        payload.tipo_tasa = "Efectiva"
        payload.capitalizacion = "Mensual" 

        tasa_ingresada = Decimal(str(payload.tasa_anual))
        if not (ifi_row.tea_min <= tasa_ingresada <= ifi_row.tea_max):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La tasa {float(tasa_ingresada):.2f}% está fuera del rango TEA "
                    f"de {payload.ifi_seleccionada} ({float(ifi_row.tea_min):.2f}% – {float(ifi_row.tea_max):.2f}%)."
                )
            )
        
        plazo_anios = payload.plazo_meses / 12
        if not (ifi_row.plazo_min_anios <= plazo_anios <= ifi_row.plazo_max_anios):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"El plazo de {payload.plazo_meses} meses ({plazo_anios:.1f} años) está fuera del rango "
                    f"de {payload.ifi_seleccionada} ({ifi_row.plazo_min_anios} – {ifi_row.plazo_max_anios} años)."
                )
            )
        
        tiene_mancomunado = False
        if role == "Cliente":
            client_obj = db.query(Client).filter(Client.codigo_cliente == current_user.codigo_usuario).first()
            if client_obj: tiene_mancomunado = client_obj.tiene_deudor_solidario
        
        payload.seguro_desgravamen = ifi_row.seguro_mancomunado if tiene_mancomunado else ifi_row.seguro_individual

    else:
        # ── MODO MANUAL ──
        if payload.tipo_tasa == "Efectiva":
            payload.capitalizacion = "Mensual"

    # ───────────────────────────────────────────────────────────────────────────

    # Tasas (Precisión 8,6)
    tasa_anual_dec = Decimal(str(payload.tasa_anual)) / Decimal("100")
    if payload.tipo_tasa == "Efectiva":
        tea = tasa_anual_dec
    else: # Nominal
        m = Decimal("12") / Decimal(str({"Mensual": 1, "Bimestral": 2, "Trimestral": 3}.get(payload.capitalizacion, 1)))
        tea = (1 + tasa_anual_dec / m)**m - 1
    
    tem = (1 + tea)**(Decimal("1")/Decimal("12")) - 1

    # Factor Francés Inicial
    n_total = payload.plazo_meses
    m_gracia = payload.meses_gracia
    n_reales = n_total - m_gracia
    
    factor = (tem * (1 + tem) ** n_reales) / ((1 + tem) ** n_reales - 1) if tem > 0 else (Decimal("1")/Decimal(str(n_reales)))
    cuota_base = monto_financiar * factor

    # 5. Cronograma detallado (Actualizado con Gracia Total y Parcial)
    detalles_db = []
    saldo = monto_financiar
    seguro_tasa = Decimal(str(payload.seguro_desgravamen))
    fecha_base = payload.fecha_inicio_prestamo or date.today()
    
    flujos_caja = [float(monto_financiar)] # Periodo 0
    total_int, total_seg = Decimal("0"), Decimal("0")

    for i in range(1, n_total + 1):
        saldo_anterior = saldo
        
        int_periodo = saldo_anterior * tem
        seguro_periodo = saldo_anterior * seguro_tasa
        
        if i <= m_gracia:
            if payload.tipo_gracia == "Total":
                # Gracia Total: Capitaliza intereses, no paga cuota.
                amort_periodo = -int_periodo 
                cuota_t = Decimal("0")
                seguro_periodo = Decimal("0") 
                saldo = saldo_anterior + int_periodo
                
                # En el último mes de gracia, recalculamos el factor y la cuota fija base al nuevo saldo inflado
                if i == m_gracia: 
                    nuevo_factor = (tem * (1 + tem) ** n_reales) / ((1 + tem) ** n_reales - 1) if tem > 0 else (Decimal("1")/Decimal(str(n_reales)))
                    cuota_base = saldo * nuevo_factor
            else: 
                # Gracia Parcial: Paga interés y seguro, amortización cero.
                amort_periodo = Decimal("0")
                cuota_t = int_periodo + seguro_periodo
                saldo = saldo_anterior
        else:
            # Periodo Regular (Sistema Francés)
            amort_periodo = cuota_base - int_periodo
            cuota_t = cuota_base + seguro_periodo
            saldo = saldo_anterior - amort_periodo
            
            # Ajuste de céntimos en la última cuota
            if i == n_total and saldo != Decimal("0"):
                cuota_t += saldo
                amort_periodo += saldo
                saldo = Decimal("0")
        
        total_int += int_periodo
        total_seg += seguro_periodo
        flujos_caja.append(-float(cuota_t))

        detalles_db.append(SimulationDetail(
            numero_cuota=i,
            # saldo_inicio=d2(saldo_anterior), 
            interes=d2(int_periodo),
            # interes_capitalizado=d2(interes_capitalizado),
            seguro=d2(seguro_periodo),
            amortizacion=d2(amort_periodo), 
            cuota_total=d2(cuota_t),
            saldo_final=d2(max(Decimal("0"), saldo)),
            # flujo_caja=d2(-cuota_t), 
            fecha_vencimiento=date(fecha_base.year + (fecha_base.month + i - 1) // 12, (fecha_base.month + i - 1) % 12 + 1, min(fecha_base.day, 28))
        ))

    # Affordability Ratio (IFM: Ingreso Familiar Mensual)
    max_cuota = max(d.cuota_total for d in detalles_db)
    ifm = Decimal("0")
    
    # Obtener entidad para IFM
    if role == "Cliente":
        entity = db.query(Client).filter(Client.codigo_cliente == current_user.codigo_usuario).first()
    else: # Asesor
        entity = db.query(Prospect).filter(Prospect.codigo_prospecto == payload.codigo_prospecto).first()
    
    if entity:
        ifm = Decimal(str(entity.ingreso_mensual)) + Decimal(str(entity.ingreso_conyuge))

    ratio = (max_cuota / ifm * 100) if ifm > 0 else Decimal("101.0") 
    
    # Límite del Fondo MiVivienda: ratio cuota/ingreso no debe superar 40%
    # para viviendas de hasta S/ 205k. Para montos mayores, se es más flexible.
    limite_ratio = Decimal("40.00") if pv_pen <= Decimal("205000.00") else Decimal("50.00")
    
    if ratio > limite_ratio:
        raise HTTPException(
            status_code=400, 
            detail=(
                f"Capacidad de pago excedida. El ratio cuota/ingreso es {float(ratio):.1f}%, "
                f"superando el límite del {float(limite_ratio):.0f}% para este tipo de vivienda."
            )
        )

    # Financieros
    try:
        tir = npf.irr(flujos_caja)
        tcea = ((1 + tir) ** 12) - 1
        van = npf.npv(float(tem), flujos_caja)
    except: tir, tcea, van = 0, 0, 0

    # 6. Persistencia
    try:
        new_sim = Simulation(
            cuota_inicial=payload.cuota_inicial, gastos_cierre=payload.gastos_cierre,
            tipo_bbp=payload.tipo_bbp, bono_bbp=bono_total,
            ifi_seleccionada=payload.ifi_seleccionada, tipo_tasa=payload.tipo_tasa,
            tasa_anual=payload.tasa_anual, plazo_meses=payload.plazo_meses,
            tipo_gracia=payload.tipo_gracia, meses_gracia=payload.meses_gracia,
            seguro_desgravamen=payload.seguro_desgravamen, fecha_inicio_prestamo=fecha_base,
            codigo_unidad=payload.codigo_unidad, codigo_cliente=payload.codigo_cliente,
            codigo_prospecto=payload.codigo_prospecto, codigo_asesor=payload.codigo_asesor
        )
        db.add(new_sim); db.flush()

        resumen = SimulationResult(
            codigo_simulacion=new_sim.codigo_simulacion,
            rango_bbp=bono_info["rango"], bono_bbp_base=bono_info["base"],
            bono_integrador_adicional=bono_info["integrador"],
            precio_neto=d2(precio_neto), monto_financiar=d2(monto_financiar),
            tasa_efectiva_anual=tea, tasa_efectiva_mensual=tem,
            factor_frances=factor, cuota_base=d2(cuota_base),
            ratio_cuota_ingreso=ratio, van=d2(van), tir=Decimal(str(tir)), tcea=Decimal(str(tcea * 100)),
            total_intereses=d2(total_int), total_pagado=d2(sum(d.cuota_total for d in detalles_db)), total_seguro=d2(total_seg)
        )
        db.add(resumen)
        for d in detalles_db: d.codigo_simulacion = new_sim.codigo_simulacion; db.add(d)
        
        db.commit(); db.refresh(new_sim)
        return new_sim

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al persistir simulación: {str(e)}")


@router.get("/", response_model=List[SimulationResponse])
def get_all_simulations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.rol_rel.tipo_rol
    if role == "Administrador":
        return db.query(Simulation).all()
    elif role == "Asesor":
        return db.query(Simulation).filter(Simulation.codigo_asesor == current_user.codigo_usuario).all()
    else:
        raise HTTPException(status_code=403, detail="No tienes permiso.")


@router.get("/me", response_model=List[SimulationResponse])
def get_my_simulations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente":
        return db.query(Simulation).filter(Simulation.codigo_cliente == current_user.codigo_usuario).all()
    elif role == "Asesor":
        return db.query(Simulation).filter(Simulation.codigo_asesor == current_user.codigo_usuario).all()
    else:
        return db.query(Simulation).all()


@router.get("/{codigo_simulacion}", response_model=SimulationResponse)
def get_simulation(
    codigo_simulacion: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim = db.query(Simulation).filter(Simulation.codigo_simulacion == codigo_simulacion).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and sim.codigo_cliente != current_user.codigo_usuario:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver esta simulación.")
    return sim


@router.get("/client/{codigo_cliente}", response_model=List[SimulationResponse])
def get_simulations_by_client(
    codigo_cliente: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and current_user.codigo_usuario != codigo_cliente:
        raise HTTPException(status_code=403, detail="No puedes ver las simulaciones de otro cliente.")
    return db.query(Simulation).filter(Simulation.codigo_cliente == codigo_cliente).all()


@router.get("/advisor/{codigo_asesor}", response_model=List[SimulationResponse])
def get_simulations_by_advisor(
    codigo_asesor: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.rol_rel.tipo_rol
    if role == "Asesor" and current_user.codigo_usuario != codigo_asesor:
        raise HTTPException(status_code=403, detail="No puedes ver las simulaciones de otro asesor.")
    return db.query(Simulation).filter(Simulation.codigo_asesor == codigo_asesor).all()


@router.get("/{codigo_simulacion}/export/excel")
def export_simulation_excel(
    codigo_simulacion: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim = db.query(Simulation).filter(Simulation.codigo_simulacion == codigo_simulacion).first()
    if not (sim and sim.resumen):
        raise HTTPException(status_code=404, detail="Simulación o resultados no encontrados")
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and sim.codigo_cliente != current_user.codigo_usuario:
        raise HTTPException(status_code=403, detail="No tienes permiso para exportar esta simulación.")

    data_detalles = [{
        "N° Cuota": d.numero_cuota,
        "Fecha Vencimiento": d.fecha_vencimiento.strftime("%d/%m/%Y"),
        "Cuota Total": float(d.cuota_total),
        "Interés": float(d.interes),
        "Amortización": float(d.amortizacion),
        "Seguro": float(d.seguro),
        "Saldo Final": float(d.saldo_final)
    } for d in sim.detalles]

    res = sim.resumen
    df_resumen = pd.DataFrame({
        "Indicador": ["VAN", "TIR", "TCEA", "Total Intereses", "Total Pagado", "Monto Financiar"],
        "Valor": [float(res.van), f"{float(res.tir)*100:.4f}%", f"{float(res.tcea):.2f}%",
                  float(res.total_intereses), float(res.total_pagado), float(res.monto_financiar)]
    })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)
        pd.DataFrame(data_detalles).to_excel(writer, sheet_name="Cronograma", index=False)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Simulacion_{codigo_simulacion}.xlsx"}
    )


@router.get("/{codigo_simulacion}/export/pdf")
def export_simulation_pdf(
    codigo_simulacion: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sim = db.query(Simulation).filter(Simulation.codigo_simulacion == codigo_simulacion).first()
    if not (sim and sim.resumen):
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente" and sim.codigo_cliente != current_user.codigo_usuario:
        raise HTTPException(status_code=403, detail="No tienes permiso para exportar esta simulación.")

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    res = sim.resumen

    elements.append(Paragraph(f"PropEquity - Propuesta Financiera #{sim.codigo_simulacion}", styles['Title']))
    elements.append(Spacer(1, 12))
    summary = f"""
    <b>Unidad:</b> {sim.unidad_rel.direccion_unidad}<br/>
    <b>Tipo BBP:</b> {sim.tipo_bbp} (S/ {res.precio_neto:,.2f} neto)<br/>
    <b>Monto Financiar:</b> S/ {res.monto_financiar:,.2f}<br/>
    <b>Tipo Tasa:</b> {sim.tipo_tasa} — {float(sim.tasa_anual):.4f}% anual<br/>
    <b>Plazo:</b> {sim.plazo_meses} meses<br/>
    <b>TCEA:</b> {res.tcea}%<br/>
    <b>VAN:</b> S/ {res.van:,.2f}<br/><b>TIR Mes:</b> {float(res.tir)*100:.4f}%
    """
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [["Cuota", "Vencimiento", "Total", "Interés", "Amortización", "Seguro", "Saldo"]]
    for d in sim.detalles:
        data.append([d.numero_cuota, d.fecha_vencimiento.strftime("%d/%m/%Y"),
                     f"{d.cuota_total:,.2f}", f"{d.interes:,.2f}", f"{d.amortizacion:,.2f}",
                     f"{d.seguro:,.2f}", f"{d.saldo_final:,.2f}"])

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    elements.append(t)
    doc.build(elements)
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename=Propuesta_{codigo_simulacion}.pdf"})