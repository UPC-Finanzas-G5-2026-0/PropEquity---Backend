from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from decimal import Decimal, ROUND_HALF_UP
import numpy_financial as npf
import pandas as pd
import io
from typing import List
from ...database import get_db
from ...models import Unit, Simulation, SimulationResult, SimulationDetail, Client, Advisor, Prospect, TipoTasa, TipoGracia
from ...schemas.simulation import SimulationCreate, SimulationResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

router = APIRouter()

def d2(val):
    """Auxiliar para redondear a 2 decimales para dinero"""
    if isinstance(val, (float, int)):
        val = Decimal(str(val))
    return val.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

@router.post("/", response_model=SimulationResponse)
def run_simulation(payload: SimulationCreate, db: Session = Depends(get_db)):
    # 1. Validaciones
    unit = db.query(Unit).filter(Unit.codigo_unidad == payload.codigo_unidad).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")

    # 2. Lógica Financiera (Inputs a Decimal)
    pv = Decimal(str(unit.precio_venta))
    cuota_inicial = payload.cuota_inicial
    bono_bbp = payload.bono_bbp
    tasa_anual_pct = payload.tasa_anual / 100
    n = payload.plazo_meses
    m_gracia = payload.meses_gracia
    codigo_t_gracia = payload.codigo_tipo_gracia
    seguro_mensual = payload.seguro_desgravamen

    # A. Intermedios
    precio_neto = pv - bono_bbp
    monto_financiar = precio_neto - cuota_inicial
    
    if payload.codigo_tipo_tasa == 2: # Efectiva
        tem = (Decimal(str(1 + tasa_anual_pct)) ** (Decimal('1') / Decimal('12'))) - 1
    else: # Nominal
        tem = Decimal(str(tasa_anual_pct)) / Decimal('12')

    n_amortizacion = n - m_gracia
    if tem > 0:
        factor = (tem * (1 + tem)**n_amortizacion) / ((1 + tem)**n_amortizacion - 1)
    else:
        factor = Decimal('1') / Decimal(str(n_amortizacion))
    
    cuota_base = monto_financiar * factor

    # 3. Generar Cronograma
    detalles_db = []
    saldo = monto_financiar
    total_int = Decimal('0')
    total_seg = Decimal('0')
    flujos_caja = [float(-monto_financiar)]

    for i in range(1, n + 1):
        interes_mes = saldo * tem
        seguro_mes = seguro_desgravamen
        
        if i <= m_gracia:
            if codigo_t_gracia == 3: # TOTAL
                pago_int = Decimal('0')
                pago_amort = Decimal('0')
                pago_cuota = Decimal('0')
                saldo = saldo + interes_mes
            elif codigo_t_gracia == 2: # PARCIAL
                pago_int = interes_mes
                pago_amort = Decimal('0')
                pago_cuota = interes_mes + seguro_mes
            else:
                pago_int = interes_mes
                pago_amort = cuota_base - interes_mes
                pago_cuota = cuota_base + seguro_mes
                saldo -= pago_amort
        else:
            pago_int = interes_mes
            pago_amort = cuota_base - interes_mes
            pago_cuota = cuota_base + seguro_mes
            saldo -= pago_amort

        total_int += pago_int
        total_seg += seguro_mensual
        flujos_caja.append(float(pago_cuota))

        detalles_db.append(SimulationDetail(
            numero_cuota=i,
            cuota_total=d2(pago_cuota),
            interes=d2(pago_int),
            amortizacion=d2(pago_amort),
            seguro=d2(seguro_mes),
            saldo_final=d2(max(0, saldo))
        ))

    total_pagado = sum(d.cuota_total for d in detalles_db)
    
    try:
        tir_m = npf.irr(flujos_caja)
        tcea = ((1 + tir_m) ** 12) - 1
        van = npf.npv(float(tem), flujos_caja)
    except:
        tir_m, tcea, van = 0, 0, 0

    # 4. PERSISTENCIA
    try:
        new_sim = Simulation(
            cuota_inicial=payload.cuota_inicial,
            bono_bbp=payload.bono_bbp,
            codigo_tipo_tasa=payload.codigo_tipo_tasa,
            tasa_anual=payload.tasa_anual,
            capitalizacion=payload.capitalizacion,
            plazo_meses=payload.plazo_meses,
            codigo_tipo_gracia=payload.codigo_tipo_gracia,
            meses_gracia=payload.meses_gracia,
            seguro_desgravamen=payload.seguro_desgravamen,
            codigo_unidad=payload.codigo_unidad,
            codigo_cliente=payload.codigo_cliente,
            codigo_prospecto=payload.codigo_prospecto,
            codigo_asesor=payload.codigo_asesor
        )
        db.add(new_sim)
        db.flush()

        resumen = SimulationResult(
            codigo_simulacion=new_sim.codigo_simulacion,
            precio_neto=d2(precio_neto),
            monto_financiar=d2(monto_financiar),
            tasa_periodica=tem,
            tasa_efectiva_mensual=tem,
            factor_frances=factor,
            van=d2(van),
            tir=Decimal(str(tir_m)),
            tcea=Decimal(str(tcea * 100)),
            total_intereses=d2(total_int),
            total_pagado=d2(total_pagado),
            total_seguro=d2(total_seg)
        )
        db.add(resumen)

        for d in detalles_db:
            d.codigo_simulacion = new_sim.codigo_simulacion
            db.add(d)

        db.commit()
        db.refresh(new_sim)
        return new_sim

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al persistir simulación: {str(e)}")

@router.get("/", response_model=List[SimulationResponse])
def get_all_simulations(db: Session = Depends(get_db)):
    """Vista de Administrador: Todo el historial."""
    return db.query(Simulation).all()

@router.get("/{codigo_simulacion}", response_model=SimulationResponse)
def get_simulation(codigo_simulacion: int, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.codigo_simulacion == codigo_simulacion).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    return sim

@router.get("/client/{codigo_cliente}", response_model=List[SimulationResponse])
def get_simulations_by_client(codigo_cliente: int, db: Session = Depends(get_db)):
    return db.query(Simulation).filter(Simulation.codigo_cliente == codigo_cliente).all()

@router.get("/advisor/{codigo_asesor}", response_model=List[SimulationResponse])
def get_simulations_by_advisor(codigo_asesor: int, db: Session = Depends(get_db)):
    return db.query(Simulation).filter(Simulation.codigo_asesor == codigo_asesor).all()

@router.get("/{codigo_simulacion}/export/excel")
def export_simulation_excel(codigo_simulacion: int, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.codigo_simulacion == codigo_simulacion).first()
    if not (sim and sim.resumen):
        raise HTTPException(status_code=404, detail="Simulación o resultados no encontrados")

    data_detalles = []
    for d in sim.detalles:
        data_detalles.append({
            "N° Cuota": d.numero_cuota,
            "Cuota Total": float(d.cuota_total),
            "Interés": float(d.interes),
            "Amortización": float(d.amortizacion),
            "Seguro": float(d.seguro),
            "Saldo Final": float(d.saldo_final)
        })
    df_detalles = pd.DataFrame(data_detalles)

    res = sim.resumen
    df_resumen = pd.DataFrame({
        "Indicador": ["VAN", "TIR", "TCEA", "Total Intereses", "Total Pagado", "Monto Financiar"],
        "Valor": [float(res.van), f"{float(res.tir)*100:.4f}%", f"{float(res.tcea):.2f}%", float(res.total_intereses), float(res.total_pagado), float(res.monto_financiar)]
    })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)
        df_detalles.to_excel(writer, sheet_name="Cronograma", index=False)
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Simulacion_{codigo_simulacion}.xlsx"}
    )

@router.get("/{codigo_simulacion}/export/pdf")
def export_simulation_pdf(codigo_simulacion: int, db: Session = Depends(get_db)):
    sim = db.query(Simulation).filter(Simulation.codigo_simulacion == codigo_simulacion).first()
    if not (sim and sim.resumen):
        raise HTTPException(status_code=404, detail="Simulación no encontrada")

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"PropEquity - Propuesta Financiera #{sim.codigo_simulacion}", styles['Title']))
    elements.append(Spacer(1, 12))

    res = sim.resumen
    summary = f"""
    <b>Unidad:</b> {sim.unidad_rel.direccion_unidad}<br/>
    <b>Monto Financiar:</b> {res.monto_financiar:,.2f}<br/>
    <b>Plazo:</b> {sim.plazo_meses} meses<br/>
    <b>TCEA:</b> {res.tcea}%<br/>
    <b>VAN:</b> {res.van:,.2f}<br/>
    <b>TIR Mes:</b> {float(res.tir)*100:.4f}%
    """
    elements.append(Paragraph(summary, styles['Normal']))
    elements.append(Spacer(1, 20))

    data = [["Cuota", "Total", "Interés", "Amortización", "Saldo"]]
    for d in sim.detalles:
        data.append([d.numero_cuota, f"{d.cuota_total:,.2f}", f"{d.interes:,.2f}", f"{d.amortizacion:,.2f}", f"{d.saldo_final:,.2f}"])

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
    elements.append(t)

    doc.build(elements)
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Propuesta_{codigo_simulacion}.pdf"})
