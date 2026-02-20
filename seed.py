from app.database import SessionLocal
from app.models import RolUsuario, Moneda, EstadoRegistroUnidad, TipoTasa, TipoGracia

def poblar_bd():
    db = SessionLocal()
    try:
        print("Insertando datos iniciales...")
        
        # 1. Insertar Roles
        roles = [RolUsuario(tipo_rol="Administrador"), RolUsuario(tipo_rol="Asesor"), RolUsuario(tipo_rol="Cliente")]
        db.add_all(roles)
        
        # 2. Insertar Monedas
        monedas = [Moneda(simbolo_moneda="PEN", tipo_moneda="Soles"), Moneda(simbolo_moneda="USD", tipo_moneda="Dólares")]
        db.add_all(monedas)
        
        # 3. Insertar Estados de Unidad
        estados = [EstadoRegistroUnidad(tipo_estado="Activo"), EstadoRegistroUnidad(tipo_estado="Inactivo")]
        db.add_all(estados)
        
        # 4. Insertar Tipos de Tasa
        tasas = [TipoTasa(tipo="Nominal"), TipoTasa(tipo="Efectiva")]
        db.add_all(tasas)
        
        # 5. Insertar Tipos de Gracia
        gracias = [TipoGracia(tipo="Ninguno"), TipoGracia(tipo="Parcial"), TipoGracia(tipo="Total")]
        db.add_all(gracias)
        
        db.commit()
        print("¡Base de datos poblada exitosamente! 🎉")
    except Exception as e:
        db.rollback()
        print(f"Hubo un error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    poblar_bd()