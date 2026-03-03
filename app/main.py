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

# --- FUNCIÓN: Súper Sembrador Automático (Roles, Ingresos, Estado Civil) ---
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

    except Exception as e:
        db.rollback()
        print(f"⚠️ Error al intentar sembrar catálogos: {e}")
    finally:
        db.close()
# ----------------------------------------------------

# --- Inicialización de Base de Datos ---
try:
    #  Esto vaciará la BD vieja para aplicar los cambios limpios
    Base.metadata.drop_all(bind=engine) 
    
    Base.metadata.create_all(bind=engine)
    configure_mappers()
    print("Conexión a base de datos PostgreSQL establecida y reiniciada.")
    
    # Ejecutar la siembra automática de catálogos
    seed_catalogs()
    
except Exception as e:
    print(f" Error crítico de Base de Datos: {e}")

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
app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(simulator.router, prefix="/api/v1/simulator", tags=["Simulación"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["Clientes"])
app.include_router(units.router, prefix="/api/v1/units", tags=["Unidades"])
app.include_router(prospects.router, prefix="/api/v1/prospects", tags=["Prospectos"])

@app.get("/")
def read_root():
    return {"message": "PropEquity API activa", "status": "Operational"}