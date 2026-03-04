
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

def run_migration():
    queries = [
        "ALTER TABLE simulation_details ADD COLUMN IF NOT EXISTS amortizacion NUMERIC(12, 2) DEFAULT 0.00;",
        "UPDATE simulation_details SET amortizacion = 0.00 WHERE amortizacion IS NULL;"
    ]
    
    with engine.connect() as conn:
        for q in queries:
            try:
                conn.execute(text(q))
                conn.commit()
                print(f"Ejecutado: {q}")
            except Exception as e:
                print(f"Error en {q}: {e}")

if __name__ == "__main__":
    run_migration()
