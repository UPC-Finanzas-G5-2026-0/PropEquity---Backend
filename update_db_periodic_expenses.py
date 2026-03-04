"""
Script para actualizar la tabla 'simulations' y 'simulation_details' 
agregando los nuevos campos de gastos periódicos.
"""
from app.database import engine
from sqlalchemy import text

def update_db():
    with engine.connect() as conn:
        print("Agregando columnas a 'simulations'...")
        try:
            conn.execute(text("ALTER TABLE simulations ADD COLUMN comision_periodica NUMERIC(12, 2) DEFAULT 0.00"))
        except Exception as e: print(f"Aviso: {e}")
        
        try:
            conn.execute(text("ALTER TABLE simulations ADD COLUMN portes NUMERIC(12, 2) DEFAULT 0.00"))
        except Exception as e: print(f"Aviso: {e}")
        
        try:
            conn.execute(text("ALTER TABLE simulations ADD COLUMN gastos_administracion NUMERIC(12, 2) DEFAULT 0.00"))
        except Exception as e: print(f"Aviso: {e}")

        print("Agregando columnas a 'simulation_details'...")
        try:
            conn.execute(text("ALTER TABLE simulation_details ADD COLUMN comisiones NUMERIC(12, 2) DEFAULT 0.00"))
        except Exception as e: print(f"Aviso: {e}")
        
        conn.commit()
        print("✅ Columnas agregadas correctamente.")

if __name__ == "__main__":
    update_db()
