import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import configure_mappers

# Importaciones locales
from .database import engine, Base
from . import models 
from .api.v1 import simulator, auth, clients, units, prospects

# 🚨 SEGURIDAD PARA RENDER: Crear carpeta 'uploads' si no existe.
# Sin esto, app.mount fallará si la carpeta no está en el repo de Git.
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Crear tablas e inicializar mappers
try:
    Base.metadata.create_all(bind=engine)
    configure_mappers()
except Exception as e:
    print(f"⚠️ Alerta de Base de Datos: {e}")

app = FastAPI(
    title="PropEquity API",
    description="API para gestión de créditos hipotecarios y simulaciones financieras.",
    version="1.0.0"
)

# Evitar problemas de redirección con barras diagonales (trailing slashes)
app.router.redirect_slashes = False

# Montar archivos estáticos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Configuración de CORS optimizada
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3003",
        "https://propequity.vercel.app",
        "https://propequity-frontend-8ht9mqt3t-renxolls-projects.vercel.app",
        # Agrega aquí tu URL final de Vercel si es distinta
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Manejadores de Excepciones (Exception Handlers) ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Maneja errores de validación de esquemas Pydantic"""
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({
            "message": "Error de validación de datos", 
            "detail": exc.errors()
        })
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Maneja errores de lógica de negocio (ValueErrors)"""
    return JSONResponse(
        status_code=422,
        content={
            "message": "Error de validación", 
            "detail": str(exc)
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Manejador global para evitar que la API devuelva errores no controlados"""
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal Server Error", 
            "detail": str(exc) if os.getenv("DEBUG") == "true" else "Ocurrió un error inesperado en el servidor."
        }
    )

# --- Inclusión de Routers ---
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])
app.include_router(simulator.router, prefix="/api/v1/simulator", tags=["Simulación"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["Clientes"])
app.include_router(units.router, prefix="/api/v1/units", tags=["Unidades"])
app.include_router(prospects.router, prefix="/api/v1/prospects", tags=["Prospectos"])

@app.get("/")
def read_root():
    return {
        "message": "Bienvenido a PropEquity API - Gestión Inmobiliaria",
        "docs": "/docs",
        "status": "Operational",
        "environment": "Production" if os.getenv("RENDER") else "Development"
    }