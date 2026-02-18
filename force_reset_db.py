import sqlite3
from app.database import engine, Base
from app.models import User, Client, Unit, Simulation, RolUsuario, Administrator, Advisor, Moneda, EstadoRegistroUnidad, TipoTasa, TipoGracia

def force_reset():
    conn = sqlite3.connect('propequity.db')
    cursor = conn.cursor()
    
    # Obtener todas las tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"Tablas encontradas: {tables}")
    
    # Desactivar llaves foráneas
    cursor.execute("PRAGMA foreign_keys = OFF;")
    
    for table in tables:
        if table != 'sqlite_sequence':
            print(f"Dropping table: {table}")
            try:
                cursor.execute(f"DROP TABLE IF EXISTS \"{table}\";")
            except Exception as e:
                print(f"Error dropping {table}: {e}")
    
    conn.commit()
    conn.close()
    print("Database wiped raw.")

    # Recrear usando SQLAlchemy
    print("Recreating tables via SQLAlchemy...")
    Base.metadata.create_all(bind=engine)
    print("Tables recreated.")

    # Seeding Roles, Currencies & Statuses
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    
    db = SessionLocal()
    
    # Roles
    roles = ['Administrador', 'Asesor', 'Cliente']
    print(f"Seeding roles: {roles}")
    for r_name in roles:
        db.add(RolUsuario(tipo_rol=r_name))
    
    # Monedas (Fixed IDs)
    monedas_data = [
        {'id': 1, 'simbolo': 'PEN', 'tipo': 'Soles'},
        {'id': 2, 'simbolo': 'USD', 'tipo': 'Dólares'}
    ]
    print(f"Seeding currencies: {monedas_data}")
    for m in monedas_data:
        db.add(Moneda(codigo_moneda=m['id'], simbolo_moneda=m['simbolo'], tipo_moneda=m['tipo']))

    # Estados de Registro (Fixed IDs)
    estados_data = [
        {'id': 1, 'val': 'Activo'},
        {'id': 2, 'val': 'Inactivo'}
    ]
    print(f"Seeding unit statuses: {estados_data}")
    for e in estados_data:
        db.add(EstadoRegistroUnidad(codigo_estado=e['id'], tipo_estado=e['val']))

    # Tipos de Tasa (Fixed IDs)
    tasas_data = [
        {'id': 1, 'val': 'Nominal'},
        {'id': 2, 'val': 'Efectiva'}
    ]
    print(f"Seeding rate types: {tasas_data}")
    for t in tasas_data:
        db.add(TipoTasa(codigo_tipo_tasa=t['id'], tipo=t['val']))
        
    # Tipos de Gracia (Fixed IDs)
    gracias_data = [
        {'id': 1, 'val': 'Ninguno'},
        {'id': 2, 'val': 'Parcial'},
        {'id': 3, 'val': 'Total'}
    ]
    print(f"Seeding grace types: {gracias_data}")
    for g in gracias_data:
        db.add(TipoGracia(codigo_tipo_gracia=g['id'], tipo=g['val']))
        
    db.commit()
    db.close()
    print("Seeds completed successfully.")

if __name__ == "__main__":
    force_reset()
