import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import configure_mappers

from .database import engine, Base, SessionLocal 
from . import models 
from .api.v1 import simulator, auth, clients, units, prospects

if not os.path.exists("uploads"):
    os.makedirs("uploads")


def seed_catalogs():
    db = SessionLocal()
    try:
        # 1. Sembrar Roles
        if db.query(models.RolUsuario).count() == 0:
            db.add_all([
                models.RolUsuario(tipo_rol="Cliente"),
                models.RolUsuario(tipo_rol="Asesor"),
                models.RolUsuario(tipo_rol="Administrador")
            ])
            db.commit()
            print("Roles creados.")

        # 2. Sembrar Tipos de Ingreso
        if db.query(models.TipoIngreso).count() == 0:
            db.add_all([
                models.TipoIngreso(nombre_tipo_ingreso="Dependiente"),
                models.TipoIngreso(nombre_tipo_ingreso="Independiente"),
                models.TipoIngreso(nombre_tipo_ingreso="Ahorro programado")
            ])
            db.commit()
            print("Tipos de ingreso creados.")

        # 3. Sembrar Estados Civiles
        if db.query(models.EstadoCivil).count() == 0:
            db.add_all([
                models.EstadoCivil(nombre_estado_civil="Soltero"),
                models.EstadoCivil(nombre_estado_civil="Casado"),
                models.EstadoCivil(nombre_estado_civil="Conviviente"),
                models.EstadoCivil(nombre_estado_civil="Divorciado"),
                models.EstadoCivil(nombre_estado_civil="Viudo")
            ])
            db.commit()
            print("Estados civiles creados.")

        # 4. Sembrar Monedas
        if db.query(models.Moneda).count() == 0:
            db.add_all([
                models.Moneda(simbolo_moneda="PEN", tipo_moneda="Soles"),
                models.Moneda(simbolo_moneda="USD", tipo_moneda="Dólares")
            ])
            db.commit()
            print("Monedas creadas.")

        # 5. Sembrar Estados de Registro de Unidad
        if db.query(models.EstadoRegistroUnidad).count() == 0:
            db.add_all([
                models.EstadoRegistroUnidad(tipo_estado="Activo"),
                models.EstadoRegistroUnidad(tipo_estado="Inactivo")
            ])
            db.commit()
            print("Estados de unidad creados.")

        # 6. Sembrar Modalidades de Vivienda
        if db.query(models.ModalidadVivienda).count() == 0:
            db.add_all([
                models.ModalidadVivienda(nombre_modalidad="Compra"),
                models.ModalidadVivienda(nombre_modalidad="Construccion"),
                models.ModalidadVivienda(nombre_modalidad="Mejoramiento")
            ])
            db.commit()
            print("Modalidades creadas.")

        # 7. Sembrar Tipos de Venta
        if db.query(models.TipoVenta).count() == 0:
            db.add_all([
                models.TipoVenta(nombre_tipo_venta="Primera venta"),
                models.TipoVenta(nombre_tipo_venta="Segunda venta")
            ])
            db.commit()
            print("Tipos de venta creados.")

        # 8. Sembrar Parámetros de Bancos (IFI) - NUEVO
        if db.query(models.CreditoIFI).count() == 0:
            bancos = [
                # Banco Pichincha
                models.CreditoIFI(nombre_ifi="Pichincha", monto_min=100, monto_max=100000, plazo_min_anios=5, plazo_max_anios=20, tea=15.00, seguro_individual=0.047, seguro_mancomunado=0.080),
                models.CreditoIFI(nombre_ifi="Pichincha", monto_min=100001, monto_max=200000, plazo_min_anios=5, plazo_max_anios=20, tea=14.00, seguro_individual=0.047, seguro_mancomunado=0.080),
                models.CreditoIFI(nombre_ifi="Pichincha", monto_min=200001, monto_max=1500000, plazo_min_anios=5, plazo_max_anios=20, tea=13.00, seguro_individual=0.047, seguro_mancomunado=0.080),
                
                # Interbank
                models.CreditoIFI(nombre_ifi="Interbank", monto_min=60000, monto_max=100000, plazo_min_anios=6, plazo_max_anios=25, tea=12.60, seguro_individual=0.028, seguro_mancomunado=0.052),
                models.CreditoIFI(nombre_ifi="Interbank", monto_min=100001, monto_max=200000, plazo_min_anios=6, plazo_max_anios=25, tea=12.30, seguro_individual=0.028, seguro_mancomunado=0.052),
                models.CreditoIFI(nombre_ifi="Interbank", monto_min=200001, monto_max=300000, plazo_min_anios=6, plazo_max_anios=25, tea=12.20, seguro_individual=0.028, seguro_mancomunado=0.052),
                models.CreditoIFI(nombre_ifi="Interbank", monto_min=300001, monto_max=1500000, plazo_min_anios=6, plazo_max_anios=25, tea=11.90, seguro_individual=0.028, seguro_mancomunado=0.052),
                
                # BBVA
                models.CreditoIFI(nombre_ifi="BBVA", monto_min=10000, monto_max=94999, plazo_min_anios=6, plazo_max_anios=12, tea=13.10, seguro_individual=0.023, seguro_mancomunado=0.043),
                models.CreditoIFI(nombre_ifi="BBVA", monto_min=95000, monto_max=450000, plazo_min_anios=6, plazo_max_anios=12, tea=12.90, seguro_individual=0.023, seguro_mancomunado=0.043),
                
                # BCP
                models.CreditoIFI(nombre_ifi="BCP", monto_min=34000, monto_max=90000, plazo_min_anios=10, plazo_max_anios=20, tea=13.99, seguro_individual=0.039, seguro_mancomunado=0.070),
                models.CreditoIFI(nombre_ifi="BCP", monto_min=90001, monto_max=240000, plazo_min_anios=10, plazo_max_anios=20, tea=13.99, seguro_individual=0.039, seguro_mancomunado=0.070),
                models.CreditoIFI(nombre_ifi="BCP", monto_min=240001, monto_max=364500, plazo_min_anios=10, plazo_max_anios=20, tea=13.99, seguro_individual=0.039, seguro_mancomunado=0.070),
                
                # GNB
                models.CreditoIFI(nombre_ifi="GNB", monto_min=30000, monto_max=1500000, plazo_min_anios=3, plazo_max_anios=25, tea=13.25, seguro_individual=0.040, seguro_mancomunado=0.075)
            ]
            db.add_all(bancos)
            db.commit()
            print("Parámetros de bancos (IFI) creados.")

        # 9. Sembrar Bonos MiVivienda (BBP) - NUEVO (Valores Actualizados 2026)
        if db.query(models.BonoBBP).count() == 0:
            bonos = [
                models.BonoBBP(rango="R1", valor_vivienda_min=68800, valor_vivienda_max=98100, bono_tradicional=27400, bono_sostenible=33700, bono_integrador_tradicional=31000, bono_integrador_sostenible=37300),
                models.BonoBBP(rango="R2", valor_vivienda_min=98101, valor_vivienda_max=146900, bono_tradicional=22800, bono_sostenible=29100, bono_integrador_tradicional=26400, bono_integrador_sostenible=32700),
                models.BonoBBP(rango="R3", valor_vivienda_min=146901, valor_vivienda_max=244600, bono_tradicional=20900, bono_sostenible=27200, bono_integrador_tradicional=24500, bono_integrador_sostenible=30800),
                models.BonoBBP(rango="R4", valor_vivienda_min=244601, valor_vivienda_max=362100, bono_tradicional=7800, bono_sostenible=14100, bono_integrador_tradicional=11400, bono_integrador_sostenible=17700),
                models.BonoBBP(rango="R5", valor_vivienda_min=362101, valor_vivienda_max=488800, bono_tradicional=0, bono_sostenible=0, bono_integrador_tradicional=0, bono_integrador_sostenible=0)
            ]
            db.add_all(bonos)
            db.commit()
            print("Bonos BBP (2026) creados.")

    except Exception as e:
        db.rollback()
        print(f"⚠️ Error al intentar sembrar catálogos: {e}")
    finally:
        db.close()


try:
    # LÍNEA COMENTADA PARA PROTEGER AL ADMIN Y TUS DATOS
    # Base.metadata.drop_all(bind=engine) 
    
    Base.metadata.create_all(bind=engine)
    configure_mappers()
    print("✅ Conexión a base de datos PostgreSQL establecida.")
    
    # Ejecutar la siembra automática de catálogos
    seed_catalogs()
    
except Exception as e:
    print(f"❌ Error crítico de Base de Datos: {e}")

app = FastAPI(
    title="PropEquity API",
    description="API para gestión de créditos hipotecarios y simulaciones financieras.",
    version="1.0.0"
)

app.router.redirect_slashes = False

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS ACTUALIZADO Y CORREGIDO
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "https://propequity.vercel.app", 
        "https://propequity-frontend.vercel.app" # <-- URL EXACTA AÑADIDA
    ],
    allow_origin_regex=r"https://.*\.vercel\.app", 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Exception Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Convertir todos los detalles de error a strings para evitar problemas de serialización
    def stringify_exceptions(obj):
        if isinstance(obj, Exception):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: stringify_exceptions(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [stringify_exceptions(v) for v in obj]
        else:
            return obj
            
    error_details = stringify_exceptions(exc.errors())
    
    # SE ELIMINARON LOS HEADERS MANUALES QUE ROMPÍAN EL CORS
    return JSONResponse(
        status_code=422,
        content={"message": "Error de validación de datos", "detail": error_details}
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    # 🚨 SE ELIMINARON LOS HEADERS MANUALES QUE ROMPÍAN EL CORS
    return JSONResponse(
        status_code=422, 
        content={"message": "Error de lógica", "detail": str(exc)}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print(f"CRITICAL ERROR: {str(exc)}")
    traceback.print_exc()
    
    # SE ELIMINARON LOS HEADERS MANUALES QUE ROMPÍAN EL CORS
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)}
    )


app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])
app.include_router(simulator.router, prefix="/api/v1/simulator", tags=["Simulación"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["Clientes"])
app.include_router(units.router, prefix="/api/v1/units", tags=["Unidades"])
app.include_router(prospects.router, prefix="/api/v1/prospects", tags=["Prospectos"])

@app.get("/")
def read_root():
    return {"message": "PropEquity API activa", "status": "Operational"}