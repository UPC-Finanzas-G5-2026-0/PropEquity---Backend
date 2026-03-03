"""
Seed script para creditos_ifi.
Borra los registros existentes y carga los datos correctos de cada IFI.

Ejecutar con:
    python seed_creditos_ifi.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models import CreditoIFI
from decimal import Decimal

db = SessionLocal()

try:
    # Limpiar tabla
    db.query(CreditoIFI).delete()
    db.commit()
    print("Tabla limpiada.")

    registros = [
        # ── Banco Pichincha ──────────────────────────────────────────────────────
        # Hasta S/ 100,000 → TEA única 15.00%
        CreditoIFI(nombre_ifi="Pichincha", monto_min=Decimal("0.00"),      monto_max=Decimal("100000.00"), plazo_min_anios=1,  plazo_max_anios=20, tea_min=Decimal("15.00"), tea_max=Decimal("15.00"), seguro_individual=Decimal("0.047"), seguro_mancomunado=Decimal("0.080")),
        # S/ 100,001 – 200,000 → TEA única 14.00%
        CreditoIFI(nombre_ifi="Pichincha", monto_min=Decimal("100001.00"), monto_max=Decimal("200000.00"), plazo_min_anios=1,  plazo_max_anios=20, tea_min=Decimal("14.00"), tea_max=Decimal("14.00"), seguro_individual=Decimal("0.047"), seguro_mancomunado=Decimal("0.080")),
        # Más de S/ 200,001 → TEA única 13.00%
        CreditoIFI(nombre_ifi="Pichincha", monto_min=Decimal("200001.00"), monto_max=None,                plazo_min_anios=1,  plazo_max_anios=20, tea_min=Decimal("13.00"), tea_max=Decimal("13.00"), seguro_individual=Decimal("0.047"), seguro_mancomunado=Decimal("0.080")),

        # ── Interbank ────────────────────────────────────────────────────────────
        # S/ 60,000 – 100,000 → 8.60% – 12.60%
        CreditoIFI(nombre_ifi="Interbank", monto_min=Decimal("60000.00"),  monto_max=Decimal("100000.00"), plazo_min_anios=6,  plazo_max_anios=25, tea_min=Decimal("8.60"),  tea_max=Decimal("12.60"), seguro_individual=Decimal("0.028"), seguro_mancomunado=Decimal("0.052")),
        # S/ 100,001 – 200,000 → 8.50% – 12.30%
        CreditoIFI(nombre_ifi="Interbank", monto_min=Decimal("100001.00"), monto_max=Decimal("200000.00"), plazo_min_anios=6,  plazo_max_anios=25, tea_min=Decimal("8.50"),  tea_max=Decimal("12.30"), seguro_individual=Decimal("0.028"), seguro_mancomunado=Decimal("0.052")),
        # S/ 200,001 – 300,000 → 8.30% – 12.20%
        CreditoIFI(nombre_ifi="Interbank", monto_min=Decimal("200001.00"), monto_max=Decimal("300000.00"), plazo_min_anios=6,  plazo_max_anios=25, tea_min=Decimal("8.30"),  tea_max=Decimal("12.20"), seguro_individual=Decimal("0.028"), seguro_mancomunado=Decimal("0.052")),
        # Más de S/ 300,001 → 8.20% – 11.90%
        CreditoIFI(nombre_ifi="Interbank", monto_min=Decimal("300001.00"), monto_max=None,                 plazo_min_anios=6,  plazo_max_anios=25, tea_min=Decimal("8.20"),  tea_max=Decimal("11.90"), seguro_individual=Decimal("0.028"), seguro_mancomunado=Decimal("0.052")),

        # ── BBVA ─────────────────────────────────────────────────────────────────
        # S/ 10,000 – 94,999 → 13.10% única
        CreditoIFI(nombre_ifi="BBVA",      monto_min=Decimal("10000.00"),  monto_max=Decimal("94999.00"),  plazo_min_anios=6,  plazo_max_anios=12, tea_min=Decimal("13.10"), tea_max=Decimal("13.10"), seguro_individual=Decimal("0.023"), seguro_mancomunado=Decimal("0.043")),
        # S/ 95,000 – 450,000 → 12.90% única
        CreditoIFI(nombre_ifi="BBVA",      monto_min=Decimal("95000.00"),  monto_max=Decimal("450000.00"), plazo_min_anios=6,  plazo_max_anios=12, tea_min=Decimal("12.90"), tea_max=Decimal("12.90"), seguro_individual=Decimal("0.023"), seguro_mancomunado=Decimal("0.043")),

        # ── BCP ──────────────────────────────────────────────────────────────────
        # S/ 34,000 – 90,000 → 13.99% única
        CreditoIFI(nombre_ifi="BCP",       monto_min=Decimal("34000.00"),  monto_max=Decimal("90000.00"),  plazo_min_anios=10, plazo_max_anios=20, tea_min=Decimal("13.99"), tea_max=Decimal("13.99"), seguro_individual=Decimal("0.039"), seguro_mancomunado=Decimal("0.070")),
        # S/ 90,001 – 240,000 → 13.99% única
        CreditoIFI(nombre_ifi="BCP",       monto_min=Decimal("90001.00"),  monto_max=Decimal("240000.00"), plazo_min_anios=10, plazo_max_anios=20, tea_min=Decimal("13.99"), tea_max=Decimal("13.99"), seguro_individual=Decimal("0.039"), seguro_mancomunado=Decimal("0.070")),
        # S/ 240,001 – 364,500 → 13.99% única
        CreditoIFI(nombre_ifi="BCP",       monto_min=Decimal("240001.00"), monto_max=Decimal("364500.00"), plazo_min_anios=10, plazo_max_anios=20, tea_min=Decimal("13.99"), tea_max=Decimal("13.99"), seguro_individual=Decimal("0.039"), seguro_mancomunado=Decimal("0.070")),

        # ── GNB ──────────────────────────────────────────────────────────────────
        # S/ 30,000 – 1,500,000 → 13.25% única
        CreditoIFI(nombre_ifi="GNB",       monto_min=Decimal("30000.00"),  monto_max=Decimal("1500000.00"),plazo_min_anios=3,  plazo_max_anios=25, tea_min=Decimal("13.25"), tea_max=Decimal("13.25"), seguro_individual=Decimal("0.040"), seguro_mancomunado=Decimal("0.075")),
    ]

    db.add_all(registros)
    db.commit()
    print(f"✅ {len(registros)} registros insertados correctamente en creditos_ifi.")

except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
    raise
finally:
    db.close()
