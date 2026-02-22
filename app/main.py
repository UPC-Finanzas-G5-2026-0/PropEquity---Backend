from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base, db_url
from . import models # Asegurar que todos los modelos se registren en Base.metadata
from .core.config import settings
from .api.v1 import simulator, auth, clients, units, prospects
print(f"DEBUG: Engine URL = {engine.url}")

# Crear tablas e inicializar mappers
Base.metadata.create_all(bind=engine)

from sqlalchemy.orm import configure_mappers
configure_mappers()

app = FastAPI(
    title="PropEquity API",
    description="API para gestión de créditos hipotecarios y simulaciones financieras.",
    version="1.0.0"
)
app.router.redirect_slashes = False

# Montar carpeta de subidas para servir imágenes
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3003",
        "http://0.0.0.0:3000",
        "https://propequity.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Handler para que los errores 422 (Validación) también tengan cabecera CORS
# y no den el error de "Network Error" en el frontend
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"message": "Error de validación de datos", "detail": exc.errors()},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

# Handler específico para errores de validación de Pydantic (ValueError en model_validator)
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    import traceback
    error_detail = str(exc) if exc else "Error de validación"
    
    return JSONResponse(
        status_code=422,
        content={"message": "Error de validación", "detail": error_detail},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    
    # Si es un ValueError, tratarlo como error de validación
    if isinstance(exc, ValueError):
        return JSONResponse(
            status_code=422,
            content={"message": "Error de validación", "detail": str(exc)},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
    
    # Para otros errores, convertir a string de forma segura
    error_detail = str(exc) if exc else "Error interno del servidor"
    
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": error_detail},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        }
    )

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
        "status": "Operational"
    }