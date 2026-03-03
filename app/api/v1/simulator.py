
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

@router.get("/tem")
def calcular_tem(tea: float):
    """
    Calcula la Tasa Efectiva Mensual (TEM) a partir de la Tasa Efectiva Anual (TEA).
    Parámetro: tea (float) en porcentaje, por ejemplo 12 para 12% anual.
    """
    tem = (1 + (tea / 100)) ** (1/12) - 1
    return {"tea": tea, "tem": round(tem * 100, 6)}

# Nuevo endpoint para guardar simulación seleccionada
@router.post("/save", response_model=SimulationResponse)
def save_simulation(
    payload: SimulationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Guarda una simulación seleccionada por el usuario. Los datos deben ser enviados desde el frontend.
    """
    try:
        new_sim = Simulation(
            cuota_inicial=payload.cuota_inicial,
            coste_notarial=payload.coste_notarial,
            coste_registral=payload.coste_registral,
            tasacion=payload.tasacion,
            comision_estudio=payload.comision_estudio,
            comision_activacion=payload.comision_activacion,
            gastos_iniciales=payload.gastos_iniciales or (payload.coste_notarial + payload.coste_registral + payload.tasacion + payload.comision_estudio + payload.comision_activacion),
            tipo_bbp=payload.tipo_bbp, bono_bbp=getattr(payload, 'bono_bbp', 0),
            categoria_integrador=getattr(payload, 'categoria_integrador', None),
            ingreso_maximo_integrador=getattr(payload, 'ingreso_maximo_integrador', None),
            ifi_seleccionada=payload.ifi_seleccionada, tipo_tasa=payload.tipo_tasa,
            tasa_anual=payload.tasa_anual, capitalizacion=payload.capitalizacion,
            plazo_meses=payload.plazo_meses, tipo_gracia=payload.tipo_gracia,
            meses_gracia=payload.meses_gracia, seguro_desgravamen=payload.seguro_desgravamen,
            fecha_inicio_prestamo=payload.fecha_inicio_prestamo,
            codigo_unidad=payload.codigo_unidad, codigo_cliente=payload.codigo_cliente,
            codigo_prospecto=payload.codigo_prospecto, codigo_asesor=payload.codigo_asesor
        )
        db.add(new_sim)
        db.commit()
        db.refresh(new_sim)
        return new_sim
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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


@router.post("/")
def run_simulation(
    payload: SimulationCreate,
    save: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"DEBUG: Payload recibido -> {payload.model_dump()}")
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

    # Validar período de gracia
    if payload.meses_gracia >= payload.plazo_meses:
        raise HTTPException(status_code=422, detail="meses_gracia debe ser menor que plazo_meses.")

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

    # Cálculo del préstamo (monto a financiar) antes de cualquier validación que lo use
    precio_neto = pv - bono_total
    # Cálculo de Gastos Iniciales 
    # Prioridad: 1. Campos desglosados, 2. Campo consolidado gastos_iniciales
    gastos_sum = Decimal(str(payload.coste_notarial or 0)) + Decimal(str(payload.coste_registral or 0)) + \
                 Decimal(str(payload.tasacion or 0)) + Decimal(str(payload.comision_estudio or 0)) + \
                 Decimal(str(payload.comision_activacion or 0))
    
    # Si la suma es 0, intentamos usar el campo consolidado
    gastos_iniciales_dec = gastos_sum if gastos_sum > 0 else Decimal(str(payload.gastos_iniciales or 0))
    
    # Aseguramos que el payload tenga el valor final para persistencia
    payload.gastos_iniciales = float(gastos_iniciales_dec)

    # 🚨 VALIDACIÓN: Gastos iniciales no pueden superar el 5% del precio de venta 🚨
    max_gastos = pv * Decimal("0.05")
    if gastos_iniciales_dec > max_gastos:
        raise HTTPException(
            status_code=400, 
            detail=f"Los gastos iniciales (S/ {float(gastos_iniciales_dec):,.2f}) exceden el límite del 5% del precio de venta (Máximo S/ {float(max_gastos):,.2f})."
        )

    cuota_inicial_dec = Decimal(str(payload.cuota_inicial))
    
    # Saldo del inmueble solamente (para tracking interno)
    saldo_inmueble = pv - cuota_inicial_dec - bono_total
    
    # MONTO TOTAL A FINANCIAR (Capital del Préstamo)
    monto_financiar = saldo_inmueble + gastos_iniciales_dec

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
        # Obtener entidad a validar (Cliente registrado o Prospecto del asesor)
        entidad = None
        if role == "Cliente":
            entidad = db.query(Client).filter(Client.codigo_cliente == current_user.codigo_usuario).first()
        elif role == "Asesor" and payload.codigo_prospecto:
            from app.models import Prospect
            entidad = db.query(Prospect).filter(Prospect.codigo_prospecto == payload.codigo_prospecto).first()

        if entidad:
            # R-FMV1: El solicitante NO debe ser propietario de vivienda
            if entidad.es_propietario_vivienda:
                raise HTTPException(
                    status_code=400,
                    detail="El solicitante ya es propietario de una vivienda. No califica para el Bono de Buen Pagador (BBP) del Fondo MiVivienda."
                )
            # R-FMV2: El cónyuge/conviviente NO debe ser propietario
            if entidad.conyuge_propietario:
                raise HTTPException(
                    status_code=400,
                    detail="El cónyuge o conviviente ya es propietario de una vivienda. No califica para el BBP del Fondo MiVivienda."
                )
            # R-FMV3: Los hijos menores NO deben ser propietarios
            if entidad.hijos_menores_propietarios:
                raise HTTPException(
                    status_code=400,
                    detail="Uno o más hijos menores de edad figura como propietario de vivienda. No califica para el BBP."
                )
            # R-FMV4: No haber recibido apoyo habitacional estatal previo
            if entidad.recibio_apoyo_estatal:
                raise HTTPException(
                    status_code=400,
                    detail="El solicitante ya recibió apoyo habitacional del Estado previamente. No califica para el Crédito MiVivienda."
                )
            # R-FMV5: No tener crédito FMV activo en este momento
            if entidad.tiene_credito_fmv_activo:
                raise HTTPException(
                    status_code=400,
                    detail="El solicitante tiene un Crédito MiVivienda activo. No puede acceder a un nuevo crédito del Fondo MiVivienda."
                )

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
        # tipo_tasa y tasa_anual se precargan/bloquean según reglas del banco
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

        # BLOQUEO: Con IFI, la tasa SIEMPRE es Efectiva (TEA)
        payload.tipo_tasa = "Efectiva"
        payload.capitalizacion = "Mensual" # Deshabilitado/Default

        tasa_ingresada = Decimal(str(payload.tasa_anual))
        if not (ifi_row.tea_min <= tasa_ingresada <= ifi_row.tea_max):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"La tasa {float(tasa_ingresada):.2f}% está fuera del rango TEA "
                    f"de {payload.ifi_seleccionada} ({float(ifi_row.tea_min):.2f}% – {float(ifi_row.tea_max):.2f}%)."
                )
            )
        
        # Validación de PLAZO específico de la IFI
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
        # Si eliges "Efectiva", capitalización no aplica (forzamos Mensual)
        if payload.tipo_tasa == "Efectiva":
            payload.capitalizacion = "Mensual"
        # Si eliges "Nominal", se usa la capitalización enviada por el usuario

    # ───────────────────────────────────────────────────────────────────────────

    # Tasas (Precisión 8,6) - Asignar tem lo más temprano posible
    tasa_anual_dec = Decimal(str(payload.tasa_anual)) / Decimal("100")
    if payload.tipo_tasa == "Efectiva":
        tea = tasa_anual_dec
    else:
        m = Decimal("12") / Decimal(str({"Mensual": 1, "Bimestral": 2, "Trimestral": 3}.get(payload.capitalizacion, 1)))
        tea = (1 + tasa_anual_dec / m)**m - 1
    tem = (1 + tea)**(Decimal("1")/Decimal("12")) - 1
    seguro_tasa = Decimal(str(payload.seguro_desgravamen)) / Decimal("100")
    n_total = payload.plazo_meses
    # Validaciones Finales de Gracia
    if payload.tipo_gracia == "Ninguno":
        m_gracia = 0
        payload.meses_gracia = 0
    else:
        m_gracia = payload.meses_gracia

    n_total = payload.plazo_meses
    n_reales = n_total - m_gracia
    
    # MÉTODO DE CÁLCULO: Usamos Tasa Combinada (TEM + Seguro) para cuota constante total
    tasa_para_factor = tem + seguro_tasa

    # Cuota Base Inicial (para los meses amortizables)
    # Usamos n_reales porque es el plazo efectivo de pago de principal
    factor = (tasa_para_factor * (1 + tasa_para_factor) ** n_reales) / ((1 + tasa_para_factor) ** n_reales - 1) if tasa_para_factor > 0 else (Decimal("1")/Decimal(str(n_reales)))
    cuota_base = monto_financiar * factor 
    
    print(f"DEBUG: Monto={monto_financiar}, TEA={tea*100}%, TEM={tem*100}%, Seg={seguro_tasa*100}%, CuotaBase={cuota_base}")

    # 5. Cronograma detallado
    saldo = monto_financiar
    fecha_base = payload.fecha_inicio_prestamo or date.today()
    flujos_caja = [float(monto_financiar)] # Periodo 0
    total_int, total_seg = Decimal("0"), Decimal("0")
    cronograma_extendido = []

    # Agregar cuota 0 al cronograma extendido (frontend)
    cronograma_extendido.append({
        "numero_cuota": 0,
        "fecha_pago": fecha_base.isoformat(),
        "tea": float(tea * 100),
        "tem": float(tem * 100),
        "plazo_gracia": "-",
        "saldo_inicial": float(monto_financiar),
        "interes": 0.0,
        "amortizacion": 0.0,
        "seguro_desgravamen": 0.0,
        "cuota": 0.0,
        "saldo_final": float(monto_financiar)
    })

    # Agregar cuota 0 al cronograma DB
    detalles_db = []
    detalles_db.append(SimulationDetail(
        numero_cuota=0,
        saldo_inicio=d2(monto_financiar),
        interes=d2(0),
        interes_capitalizado=d2(0),
        seguro=d2(0),
        amortizacion=d2(0),
        cuota_total=d2(0),
        saldo_final=d2(monto_financiar),
        flujo_caja=d2(0),
        fecha_vencimiento=date.today()
    ))

    for i in range(1, n_total + 1):
        saldo_anterior = saldo
        interes_capitalizado = Decimal("0")
        
        int_periodo = saldo_anterior * tem
        seguro_periodo = saldo_anterior * seguro_tasa
        
        # Solo entramos a lógica de gracia si tipo_gracia != "Ninguno"
        if payload.tipo_gracia != "Ninguno" and i <= m_gracia:
            if payload.tipo_gracia == "Total":
                # Gracia Total: No se paga nada, intereses y SEGURO se capitalizan (o solo intereses según SBS)
                # En este modelo capitalizamos solo intereses, el seguro se asume cubierto por el banco o diferido.
                interes_capitalizado = int_periodo
                amort_periodo = Decimal("0")
                seguro_pago = Decimal("0") # El cliente no paga seguro este mes
                cuota_t = Decimal("0")
                saldo = saldo_anterior + interes_capitalizado
            else: 
                # Gracia Parcial: Cuota = Saldo Inicial × TEM (solo interés). Amortización = 0. Seguro = 0.
                amort_periodo = Decimal("0")
                seguro_pago = Decimal("0")
                cuota_t = int_periodo  # int_periodo = saldo_anterior * tem
                saldo = saldo_anterior
            
            # Recalcular la cuota base en el último mes de gracia para asegurar que el capital inflado se pague exacto
            if i == m_gracia:
                n_restantes = n_total - m_gracia
                factor_p = (tasa_para_factor * (1 + tasa_para_factor) ** n_restantes) / ((1 + tasa_para_factor) ** n_restantes - 1) if tasa_para_factor > 0 else (Decimal("1")/Decimal(str(n_restantes)))
                cuota_base = saldo * factor_p
        else:
            # Amortización normal (Sistema Francés) con Tasa Combinada
            # Cuota = Amortización + Interés + Seguro -> Amortización = Cuota - Interés - Seguro
            seguro_pago = seguro_periodo
            amort_periodo = cuota_base - int_periodo - seguro_pago
            cuota_t = cuota_base
            saldo = saldo_anterior - amort_periodo
        
        total_int += int_periodo
        total_seg += seguro_pago
        flujos_caja.append(-float(cuota_t))
        fecha_pago = date(fecha_base.year + (fecha_base.month + i - 1) // 12, (fecha_base.month + i - 1) % 12 + 1, min(fecha_base.day, 28))

        # Definir texto de plazo de gracia por fila
        if payload.tipo_gracia != "Ninguno" and i <= m_gracia:
            plazo_gracia_txt = f"Gracia {payload.tipo_gracia}"
        else:
            plazo_gracia_txt = "Sin Gracia"

        cronograma_extendido.append({
            "numero_cuota": i,
            "fecha_pago": fecha_pago.isoformat(),
            "tea": float(tea * 100),
            "tem": float(tem * 100),
            "plazo_gracia": plazo_gracia_txt,
            "saldo_inicial": float(saldo_anterior),
            "interes": float(int_periodo),
            "amortizacion": float(amort_periodo),
            "seguro_desgravamen": float(seguro_periodo),
            "cuota": float(cuota_t),
            "saldo_final": float(max(Decimal("0"), saldo))
        })

        detalles_db.append(SimulationDetail(
            numero_cuota=i,
            saldo_inicio=d2(saldo_anterior), 
            interes=d2(int_periodo),
            interes_capitalizado=d2(interes_capitalizado),
            seguro=d2(seguro_periodo),
            amortizacion=d2(amort_periodo),
            cuota_total=d2(cuota_t),
            saldo_final=d2(max(Decimal("0"), saldo)),
            flujo_caja=d2(-cuota_t), 
            fecha_vencimiento=fecha_pago
        ))

    # Affordability Ratio (IFM: Ingreso Familiar Mensual)
    max_cuota = max(d.cuota_total for d in detalles_db)
    ifm = Decimal("0")
    
    # Obtener entidad para IFM
    entity = None
    if role == "Cliente":
        entity = db.query(Client).filter(Client.codigo_cliente == current_user.codigo_usuario).first()
    elif role == "Asesor" and payload.codigo_prospecto:
        entity = db.query(Prospect).filter(Prospect.codigo_prospecto == payload.codigo_prospecto).first()
    # Administrador: no tiene entidad asociada, se omite validación de capacidad de pago
    
    if entity:
        ifm = Decimal(str(entity.ingreso_mensual or 0)) + Decimal(str(entity.ingreso_conyuge or 0))

    ratio = (max_cuota / ifm * 100) if ifm > 0 else Decimal("0")
    
    # Límite del Fondo MiVivienda: ratio cuota/ingreso no debe superar 40%
    # para viviendas de hasta S/ 205k. Para montos mayores, se es más flexible.
    # Solo validar si hay datos de ingreso (excluye Admin sin entidad asociada)
    if ifm > 0:
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

    # Respuesta base (se usa tanto en preview como en guardado)
    resumen_dict = {
        "rango_bbp": bono_info["rango"],
        "bono_bbp_base": float(bono_info["base"]),
        "bono_integrador_adicional": float(bono_info["integrador"]),
        "precio_neto": float(precio_neto),
        "monto_financiar": float(monto_financiar),
        "tasa_efectiva_anual": float(tea) * 100,
        "tasa_efectiva_mensual": float(tem) * 100,
        "factor_frances": float(factor),
        "cuota_base": float(cuota_base),
        "ratio_cuota_ingreso": float(ratio),
        "van": float(van),
        "tir": float(tir),
        "tcea": float(tcea * 100),
        "total_intereses": float(total_int),
        "total_pagado": float(sum(d.cuota_total for d in detalles_db)),
        "total_seguro": float(total_seg)
    }

    # 6. Persistencia (sólo si save=True)
    try:
        if not save:
            # Modo PREVIEW: devolver cronograma sin guardar en BD
            return {
                "codigo_simulacion": None,
                "fecha_simulacion": date.today().isoformat(),
                "fecha_inicio_prestamo": fecha_base.isoformat(),
                "cuota_inicial": float(payload.cuota_inicial),
                "gastos_iniciales": float(payload.gastos_iniciales),
                "tipo_bbp": payload.tipo_bbp,
                "bono_bbp": float(bono_total),
                "tipo_tasa": payload.tipo_tasa,
                "tasa_anual": float(payload.tasa_anual),
                "plazo_meses": payload.plazo_meses,
                "tipo_gracia": payload.tipo_gracia,
                "meses_gracia": payload.meses_gracia,
                "seguro_desgravamen": float(payload.seguro_desgravamen),
                "codigo_unidad": payload.codigo_unidad,
                "resumen": resumen_dict,
                "cronograma": cronograma_extendido
            }

        # Modo GUARDAR: persistir en BD
        new_sim = Simulation(
            cuota_inicial=payload.cuota_inicial,
            coste_notarial=payload.coste_notarial,
            coste_registral=payload.coste_registral,
            tasacion=payload.tasacion,
            comision_estudio=payload.comision_estudio,
            comision_activacion=payload.comision_activacion,
            gastos_iniciales=payload.gastos_iniciales,
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
        return {
            "codigo_simulacion": new_sim.codigo_simulacion,
            "fecha_simulacion": new_sim.fecha_simulacion,
            "fecha_inicio_prestamo": new_sim.fecha_inicio_prestamo,
            "cuota_inicial": new_sim.cuota_inicial,
            "gastos_iniciales": new_sim.gastos_iniciales,
            "coste_notarial": new_sim.coste_notarial,
            "coste_registral": new_sim.coste_registral,
            "tasacion": new_sim.tasacion,
            "comision_estudio": new_sim.comision_estudio,
            "comision_activacion": new_sim.comision_activacion,
            "tipo_bbp": new_sim.tipo_bbp,
            "bono_bbp": new_sim.bono_bbp,
            "categoria_integrador": new_sim.categoria_integrador,
            "ingreso_maximo_integrador": new_sim.ingreso_maximo_integrador,
            "ifi_seleccionada": new_sim.ifi_seleccionada,
            "tipo_tasa": new_sim.tipo_tasa,
            "tasa_anual": float(new_sim.tasa_anual),
            "capitalizacion": new_sim.capitalizacion,
            "plazo_meses": new_sim.plazo_meses,
            "tipo_gracia": new_sim.tipo_gracia,
            "meses_gracia": new_sim.meses_gracia,
            "seguro_desgravamen": float(new_sim.seguro_desgravamen),
            "codigo_unidad": new_sim.codigo_unidad,
            "codigo_cliente": new_sim.codigo_cliente,
            "codigo_prospecto": new_sim.codigo_prospecto,
            "codigo_asesor": new_sim.codigo_asesor,
            "resumen": resumen_dict,
            "cronograma": cronograma_extendido
        }
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def get_all_simulations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.rol_rel.tipo_rol
    if role == "Administrador":
        sims = db.query(Simulation).all()
    elif role == "Asesor":
        sims = db.query(Simulation).filter(Simulation.codigo_asesor == current_user.codigo_usuario).all()
    else:
        raise HTTPException(status_code=403, detail="No tienes permiso.")
    return [_sim_to_dict(s) for s in sims]


def _sim_to_dict(sim: Simulation) -> dict:
    """Convierte un objeto Simulation ORM a dict completo con campos de relaciones."""
    resumen = sim.resumen
    unidad = sim.unidad_rel
    return {
        "codigo_simulacion": sim.codigo_simulacion,
        "fecha_simulacion": sim.fecha_simulacion,
        "fecha_inicio_prestamo": sim.fecha_inicio_prestamo,
        "cuota_inicial": float(sim.cuota_inicial or 0),
        "gastos_iniciales": float(sim.gastos_iniciales or 0),
        "coste_notarial": float(sim.coste_notarial or 0),
        "coste_registral": float(sim.coste_registral or 0),
        "tasacion": float(sim.tasacion or 0),
        "comision_estudio": float(sim.comision_estudio or 0),
        "comision_activacion": float(sim.comision_activacion or 0),
        "tipo_bbp": sim.tipo_bbp,
        "bono_bbp": float(sim.bono_bbp or 0),
        "categoria_integrador": sim.categoria_integrador,
        "ingreso_maximo_integrador": float(sim.ingreso_maximo_integrador) if sim.ingreso_maximo_integrador else None,
        "ifi_seleccionada": sim.ifi_seleccionada,
        "tipo_tasa": sim.tipo_tasa,
        "tasa_anual": float(sim.tasa_anual or 0),
        "capitalizacion": sim.capitalizacion,
        "plazo_meses": sim.plazo_meses,
        "tipo_gracia": sim.tipo_gracia,
        "meses_gracia": sim.meses_gracia,
        "seguro_desgravamen": float(sim.seguro_desgravamen or 0),
        "codigo_unidad": sim.codigo_unidad,
        "codigo_cliente": sim.codigo_cliente,
        "codigo_prospecto": sim.codigo_prospecto,
        "codigo_asesor": sim.codigo_asesor,
        # Campos de relación: unidad
        "direccion_unidad": unidad.direccion_unidad if unidad else None,
        "distrito_unidad": unidad.distrito_unidad if unidad else None,
        # Campos de relación: resumen financiero
        "monto_financiamiento": float(resumen.monto_financiar) if resumen else 0.0,
        "cuota_mensual": float(resumen.cuota_base) if resumen else 0.0,
        "resumen": {
            "rango_bbp": resumen.rango_bbp,
            "bono_bbp_base": float(resumen.bono_bbp_base),
            "bono_integrador_adicional": float(resumen.bono_integrador_adicional),
            "precio_neto": float(resumen.precio_neto),
            "monto_financiar": float(resumen.monto_financiar),
            "tasa_efectiva_anual": float(resumen.tasa_efectiva_anual) * 100,
            "tasa_efectiva_mensual": float(resumen.tasa_efectiva_mensual) * 100,
            "factor_frances": float(resumen.factor_frances),
            "cuota_base": float(resumen.cuota_base),
            "ratio_cuota_ingreso": float(resumen.ratio_cuota_ingreso),
            "van": float(resumen.van),
            "tir": float(resumen.tir),
            "tcea": float(resumen.tcea),
            "total_intereses": float(resumen.total_intereses),
            "total_pagado": float(resumen.total_pagado),
            "total_seguro": float(resumen.total_seguro)
        } if resumen else None,
        "detalles": [
            {
                "numero_cuota": d.numero_cuota,
                "fecha_vencimiento": d.fecha_vencimiento.isoformat() if d.fecha_vencimiento else None,
                "fecha_pago": d.fecha_vencimiento.isoformat() if d.fecha_vencimiento else None,
                "tea": float(resumen.tasa_efectiva_anual * 100) if resumen else 0.0,
                "tem": float(resumen.tasa_efectiva_mensual * 100) if resumen else 0.0,
                "plazo_gracia": "Sin Gracia",
                "saldo_inicio": float(d.saldo_inicio),
                "saldo_inicial": float(d.saldo_inicio),
                "interes": float(d.interes),
                "amortizacion": float(d.amortizacion),
                "seguro": float(d.seguro),
                "seguro_desgravamen": float(d.seguro),
                "cuota_total": float(d.cuota_total),
                "cuota": float(d.cuota_total),
                "saldo_final": float(d.saldo_final),
            }
            for d in sorted(sim.detalles, key=lambda x: x.numero_cuota)
        ]
    }


@router.get("/me")
def get_my_simulations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.rol_rel.tipo_rol
    if role == "Cliente":
        sims = db.query(Simulation).filter(Simulation.codigo_cliente == current_user.codigo_usuario).all()
    elif role == "Asesor":
        sims = db.query(Simulation).filter(Simulation.codigo_asesor == current_user.codigo_usuario).all()
    else:
        sims = db.query(Simulation).all()
    return [_sim_to_dict(s) for s in sims]


@router.get("/{codigo_simulacion}")
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
    return _sim_to_dict(sim)


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

    try:
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        res = sim.resumen
        detalles = sorted(sim.detalles, key=lambda x: x.numero_cuota)

        C_DARK, C_ORANGE, C_BLUE = "0F172A", "F97316", "3B82F6"
        C_LIGHT, C_ROW2, C_WHITE = "F8FAFC", "EFF6FF", "FFFFFF"
        C_GRAY, C_NAVY = "94A3B8", "1E293B"

        def fill(c): return PatternFill("solid", fgColor=c)
        def tb():
            s = Side(style="thin", color="E2E8F0")
            return Border(left=s, right=s, top=s, bottom=s)
        def hf(size=9, color=C_WHITE): return Font(name="Calibri", bold=True, color=color, size=size)
        def bf(bold=False, color=C_DARK, size=9): return Font(name="Calibri", bold=bold, color=color, size=size)
        def al(h="center", v="center"): return Alignment(horizontal=h, vertical=v)
        def mv(v): return float(v) if v is not None else 0.0

        wb = Workbook()
        # ─── Hoja 1: Resumen ────────────────────────────────────────────────
        ws = wb.active; ws.title = "Resumen"
        ws.sheet_view.showGridLines = False
        ws.merge_cells("A1:D1")
        ws["A1"].value = "PROPEQUITY — Propuesta Financiera"
        ws["A1"].font = Font(name="Calibri", bold=True, color=C_WHITE, size=15)
        ws["A1"].fill, ws["A1"].alignment = fill(C_DARK), al()
        ws.row_dimensions[1].height = 34
        ws.merge_cells("A2:D2")
        ws["A2"].value = f"Simulación #{sim.codigo_simulacion}  ·  Unidad: {sim.codigo_unidad}  ·  {sim.fecha_simulacion.strftime('%d/%m/%Y') if sim.fecha_simulacion else ''}"
        ws["A2"].font = Font(name="Calibri", bold=True, color=C_ORANGE, size=9)
        ws["A2"].fill, ws["A2"].alignment = fill(C_NAVY), al()
        ws.row_dimensions[2].height = 18
        ws.row_dimensions[3].height = 6
        for col, (txt, bg) in enumerate([("Indicador", C_BLUE), ("Valor", C_BLUE), ("Parámetro", C_ORANGE), ("Detalle", C_ORANGE)], 1):
            c = ws.cell(row=4, column=col, value=txt)
            c.font, c.fill, c.alignment, c.border = hf(), fill(bg), al(), tb()
        ws.row_dimensions[4].height = 22
        indicadores = [
            ("Monto a Financiar",  f"S/ {mv(res.monto_financiar):,.2f}"),
            ("Cuota Base",         f"S/ {mv(res.cuota_base):,.2f}"),
            ("TEA",                f"{mv(res.tasa_efectiva_anual)*100:.4f}%"),
            ("TEM",                f"{mv(res.tasa_efectiva_mensual)*100:.6f}%"),
            ("TCEA",               f"{mv(res.tcea):.2f}%"),
            ("VAN",                f"S/ {mv(res.van):,.2f}"),
            ("TIR (mensual)",      f"{mv(res.tir)*100:.4f}%"),
            ("Total Intereses",    f"S/ {mv(res.total_intereses):,.2f}"),
            ("Total Pagado",       f"S/ {mv(res.total_pagado):,.2f}"),
            ("Total Seguro",       f"S/ {mv(res.total_seguro):,.2f}"),
        ]
        parametros = [
            ("IFI",           sim.ifi_seleccionada or "Genérico"),
            ("Tipo de Tasa",  sim.tipo_tasa),
            ("Tasa Anual",    f"{float(sim.tasa_anual):.2f}%"),
            ("Plazo",         f"{sim.plazo_meses} meses"),
            ("Tipo BBP",      sim.tipo_bbp),
            ("Bono BBP",      f"S/ {mv(sim.bono_bbp):,.2f}"),
            ("Tipo Gracia",   sim.tipo_gracia),
            ("Meses Gracia",  str(sim.meses_gracia)),
            ("Seg. Desgrav.", f"{float(sim.seguro_desgravamen):.4f}%"),
            ("Rango BBP",     res.rango_bbp or "—"),
        ]
        for i, ((ind, val), (par, det)) in enumerate(zip(indicadores, parametros)):
            row = 5 + i; bg = C_LIGHT if i % 2 == 0 else C_ROW2
            ws.row_dimensions[row].height = 18
            for col, (txt, bold, h) in enumerate([(ind, False, "left"), (val, True, "right"), (par, False, "left"), (det, True, "right")], 1):
                c = ws.cell(row=row, column=col, value=txt)
                c.font, c.fill, c.border, c.alignment = bf(bold=bold, color=C_DARK if bold else C_GRAY), fill(bg), tb(), al(h=h)
        for col, w in zip("ABCD", [24, 22, 22, 20]): ws.column_dimensions[col].width = w

        # ─── Hoja 2: Cronograma ─────────────────────────────────────────────
        ws2 = wb.create_sheet("Cronograma de Pagos")
        ws2.sheet_view.showGridLines = False
        ws2.merge_cells("A1:H1")
        ws2["A1"].value = "CRONOGRAMA DE PAGOS — PropEquity"
        ws2["A1"].font = Font(name="Calibri", bold=True, color=C_WHITE, size=13)
        ws2["A1"].fill, ws2["A1"].alignment = fill(C_DARK), al()
        ws2.row_dimensions[1].height = 30
        ws2.merge_cells("A2:H2")
        ws2["A2"].value = f"Sim #{sim.codigo_simulacion}  |  S/ {mv(res.monto_financiar):,.2f}  |  {sim.plazo_meses} m  |  TEA {mv(res.tasa_efectiva_anual)*100:.2f}%  |  TCEA {mv(res.tcea):.2f}%"
        ws2["A2"].font = Font(name="Calibri", bold=True, color=C_ORANGE, size=8)
        ws2["A2"].fill, ws2["A2"].alignment = fill(C_NAVY), al()
        ws2.row_dimensions[2].height = 16; ws2.row_dimensions[3].height = 6
        hdrs = [("N°", 7), ("Fecha Pago", 13), ("Saldo Inicial", 16), ("Interés", 14),
                ("Amortización", 14), ("Seg. Desgrav.", 14), ("Cuota Total", 14), ("Saldo Final", 16)]
        ws2.row_dimensions[4].height = 22
        for col, (hdr, w) in enumerate(hdrs, 1):
            c = ws2.cell(row=4, column=col, value=hdr)
            c.font, c.fill, c.alignment, c.border = hf(), fill(C_ORANGE), al(), tb()
            ws2.column_dimensions[get_column_letter(col)].width = w
        for i, d in enumerate(detalles):
            row = 5 + i; bg = "DBEAFE" if d.numero_cuota == 0 else (C_LIGHT if i % 2 == 0 else C_ROW2)
            ws2.row_dimensions[row].height = 15
            row_vals = [d.numero_cuota,
                        d.fecha_vencimiento.strftime("%d/%m/%Y") if d.fecha_vencimiento else "—",
                        mv(d.saldo_inicio), mv(d.interes), mv(d.amortizacion),
                        mv(d.seguro), mv(d.cuota_total), mv(d.saldo_final)]
            for col, val in enumerate(row_vals, 1):
                c = ws2.cell(row=row, column=col, value=val)
                is_cuota = col == 7; is_num = col >= 3
                c.font = bf(bold=is_cuota, color=C_ORANGE if is_cuota else C_DARK)
                c.fill, c.border = fill(bg), tb()
                c.alignment = al(h="right") if col >= 3 else al()
                if is_num: c.number_format = "#,##0.00"
        tr = 5 + len(detalles); ws2.row_dimensions[tr].height = 20
        ws2.merge_cells(f"A{tr}:B{tr}")
        c = ws2[f"A{tr}"]; c.value = "TOTALES"; c.font = hf(); c.fill = fill(C_DARK); c.alignment = al(); c.border = tb()
        total_map = {4: mv(res.total_intereses), 6: mv(res.total_seguro), 7: mv(res.total_pagado)}
        for col in range(3, 9):
            c = ws2.cell(row=tr, column=col, value=total_map.get(col))
            c.font, c.fill, c.border, c.alignment, c.number_format = hf(color=C_ORANGE), fill(C_DARK), tb(), al(h="right"), "#,##0.00"

        output = io.BytesIO()
        wb.save(output); output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=PropEquity_Sim_{codigo_simulacion}.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")


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