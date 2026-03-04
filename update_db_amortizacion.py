
import os
import sys
from sqlalchemy import create_engine, text

# Agregar el directorio actual al path para importar app
sys.path.append(os.getcwd())

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL
if not DATABASE_URL:
    print("Error: DATABASE_URL no encontrada en settings.")
    exit(1)

# Asegurar formato postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def update_db():
    queries = [
        # 1. Agregar columna amortizacion a simulation_details
        "ALTER TABLE simulation_details ADD COLUMN IF NOT EXISTS amortizacion NUMERIC(12, 2) DEFAULT 0.00;",
        
        # 2. Re-verificar otras columnas críticas por si acaso
        "ALTER TABLE simulation_results ADD COLUMN IF NOT EXISTS tasa_descuento NUMERIC(8, 6) DEFAULT 8.00;",
        "ALTER TABLE simulation_results ADD COLUMN IF NOT EXISTS tasa_descuento_mensual NUMERIC(10, 8) DEFAULT 0.643403;",
        "ALTER TABLE simulation_details ADD COLUMN IF NOT EXISTS comision_periodica NUMERIC(12, 2) DEFAULT 0.00;",
        "ALTER TABLE simulation_details ADD COLUMN IF NOT EXISTS portes NUMERIC(12, 2) DEFAULT 0.00;",
        "ALTER TABLE simulation_details ADD COLUMN IF NOT EXISTS gastos_administracion NUMERIC(12, 2) DEFAULT 0.00;"
    ]
    
    with engine.connect() as conn:
        for q in queries:
            try:
                conn.execute(text(q))
                conn.commit()
                print(f"Ejecutado correctamente: {q}")
            except Exception as e:
                print(f"Error en query '{q}': {e}")

if __name__ == "__main__":
    update_db()
