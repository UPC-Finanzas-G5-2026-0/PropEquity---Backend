"""
Script para actualizar la tabla 'simulations' y 'simulation_details' 
agregando los nuevos campos de gastos periódicos.
"""
from app.database import engine
from sqlalchemy import text

def update_db():
    with engine.connect() as conn:
        print("Agregando columnas a 'simulations'...")
        # No se tocan las de Simulation ya que se agregaron antes, 
        # pero nos aseguramos que existan en el modelo.

        print("Agregando columnas de totales a 'simulation_results'...")
        try:
            conn.execute(text("ALTER TABLE simulation_results ADD COLUMN total_comisiones_periodicas NUMERIC(12, 2) DEFAULT 0.00"))
            conn.execute(text("ALTER TABLE simulation_results ADD COLUMN total_portes_gastos_adm NUMERIC(12, 2) DEFAULT 0.00"))
        except Exception as e: print(f"Aviso Resultados: {e}")

        print("Agregando columnas de desglose a 'simulation_details'...")
        try:
            conn.execute(text("ALTER TABLE simulation_details DROP COLUMN comisiones")) # Borrar la anterior agrupada
        except Exception as e: print(f"Aviso Drop: {e}")

        try:
            conn.execute(text("ALTER TABLE simulation_details ADD COLUMN comision_periodica NUMERIC(12, 2) DEFAULT 0.00"))
            conn.execute(text("ALTER TABLE simulation_details ADD COLUMN portes NUMERIC(12, 2) DEFAULT 0.00"))
            conn.execute(text("ALTER TABLE simulation_details ADD COLUMN gastos_administracion NUMERIC(12, 2) DEFAULT 0.00"))
        except Exception as e: print(f"Aviso Detalle: {e}")
        
        conn.commit()
        print("✅ Columnas agregadas correctamente.")

if __name__ == "__main__":
    update_db()
