import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import configure_mappers

# Importaciones locales
from .database import engine, Base, SessionLocal 
from . import models 
from .api.v1 import simulator, auth, clients, units, prospects

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# --- FUNCIÓN: Súper Sembrador Automático COMPLETO ---
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
            print("✅ Roles creados.")

        # 2. Sembrar Tipos de Ingreso
        if db.query(models.TipoIngreso).count() == 0:
            db.add_all([
                models.TipoIngreso(nombre_tipo_ingreso="Dependiente"),
                models.TipoIngreso(nombre_tipo_ingreso="Independiente"),
                models.TipoIngreso(nombre_tipo_ingreso="Ahorro programado")
            ])
            db.commit()
            print("✅ Tipos de ingreso creados.")

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
            print("✅ Estados civiles creados.")

        # 4. Sembrar Monedas
        if db.query(models.Moneda).count() == 0:
            db.add_all([
                models.Moneda(simbolo_moneda="PEN", tipo_moneda="Soles"),
                models.Moneda(simbolo_moneda="USD", tipo_moneda="Dólares")
            ])
            db.commit()
            print("✅ Monedas creadas.")

        # 5. Sembrar Estados de Registro de Unidad
        if db.query(models.EstadoRegistroUnidad).count() == 0:
            db.add_all([
                models.EstadoRegistroUnidad(tipo_estado="Activo"),
                models.EstadoRegistroUnidad(tipo_estado="Inactivo")
            ])
            db.commit()
            print("✅ Estados de unidad creados.")

        # 6. Sembrar Modalidades de Vivienda
        if db.query(models.ModalidadVivienda).count() == 0:
            db.add_all([
                models.ModalidadVivienda(nombre_modalidad="Compra"),
                models.ModalidadVivienda(nombre_modalidad="Construccion"),
                models.ModalidadVivienda(nombre_modalidad="Mejoramiento")
            ])
            db.commit()
            print("✅ Modalidades creadas.")

        # 7. Sembrar Tipos de Venta
        if db.query(models.TipoVenta).count() == 0:
            db.add_all([
                models.TipoVenta(nombre_tipo_venta="Primera venta"),
                models.TipoVenta(nombre_tipo_venta="Segunda venta")
            ])
            db.commit()
            print("✅ Tipos de venta creados.")

        # 8. Sembrar Parámetros de Bancos (IFI) - NUEVO
        if db.query(models.CreditoIFI).count() == 0:
            bancos = [
                models.CreditoIFI(nombre_ifi="BCP", monto_min=10000, monto_max=1500000, plazo_min_anios=5, plazo_max_anios=25, tea_min=8.5, tea_max=15.0, seguro_individual=0.028, seguro_mancomunado=0.050),
                models.CreditoIFI(nombre_ifi="BBVA", monto_min=10000, monto_max=1500000, plazo_min_anios=5, plazo_max_anios=25, tea_min=9.0, tea_max=16.0, seguro_individual=0.030, seguro_mancomunado=0.055),
                models.CreditoIFI(nombre_ifi="Interbank", monto_min=10000, monto_max=1500000, plazo_min_anios=5, plazo_max_anios=25, tea_min=8.8, tea_max=15.5, seguro_individual=0.025, seguro_mancomunado=0.045),
                models.CreditoIFI(nombre_ifi="Pichincha", monto_min=10000, monto_max=1500000, plazo_min_anios=5, plazo_max_anios=25, tea_min=9.5, tea_max=17.0, seguro_individual=0.035, seguro_mancomunado=0.060),
                models.CreditoIFI(nombre_ifi="GNB", monto_min=10000, monto_max=1500000, plazo_min_anios=5, plazo_max_anios=25, tea_min=9.2, tea_max=16.5, seguro_individual=0.032, seguro_mancomunado=0.058)
            ]
            db.add_all(bancos)
            db.commit()
            print("✅ Parámetros de bancos (IFI) creados.")

        # 9. Sembrar Bonos MiVivienda (BBP) - NUEVO
        if db.query(models.BonoBBP).count() == 0:
            bonos = [
                models.BonoBBP(rango="R1", valor_vivienda_min=65000, valor_vivienda_max=93100, bono_tradicional=25700, bono_sostenible=31100, bono_integrador_tradicional=29200, bono_integrador_sostenible=34600),
                models.BonoBBP(rango="R2", valor_vivienda_min=93100, valor_vivienda_max=139400, bono_tradicional=21400, bono_sostenible=26800, bono_integrador_tradicional=24900, bono_integrador_sostenible=30300),
                models.BonoBBP(rango="R3", valor_vivienda_min=139400, valor_vivienda_max=232200, bono_tradicional=19600, bono_sostenible=25000, bono_integrador_tradicional=23100, bono_integrador_sostenible=28500),
                models.BonoBBP(rango="R4", valor_vivienda_min=232200, valor_vivienda_max=343900, bono_tradicional=7300, bono_sostenible=12700, bono_integrador_tradicional=10800, bono_integrador_sostenible=16200),
                models.BonoBBP(rango="R5", valor_vivienda_min=343900, valor_vivienda_max=464200, bono_tradicional=0, bono_sostenible=5400, bono_integrador_tradicional=3500, bono_integrador_sostenible=8900)
            ]
            db.add_all(bonos)
            db.commit()
            print("✅ Bonos BBP creados.")

    except Exception as e:
        db.rollback()
        print(f"⚠️ Error al intentar sembrar catálogos: {e}")
    finally:
        db.close()
# ----------------------------------------------------

# --- Inicialización de Base de Datos ---
try:
    # 🚨 LÍNEA COMENTADA PARA PROTEGER AL ADMIN Y TUS DATOS
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "https://propequity.vercel.app", 
    ],
    allow_origin_regex=r"https://.*\.vercel\.app", 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Exception Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"message": "Error de validación de datos", "detail": exc.errors()})
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"message": "Error de lógica", "detail": str(exc)})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc) if os.getenv("DEBUG") == "true" else "Error inesperado."}
    )

# --- Routers ---
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])
app.include_router(simulator.router, prefix="/api/v1/simulator", tags=["Simulación"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["Clientes"])
app.include_router(units.router, prefix="/api/v1/units", tags=["Unidades"])
app.include_router(prospects.router, prefix="/api/v1/prospects", tags=["Prospectos"])

@app.get("/")
def read_root():
    return {"message": "PropEquity API activa", "status": "Operational"}