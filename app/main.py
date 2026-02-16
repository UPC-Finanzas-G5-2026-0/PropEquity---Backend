from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base

from .api.v1 import simulator 
from .api.v1 import auth      

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PropEquity API",
    description="API para gestión de créditos hipotecarios y simulaciones financieras.",
    version="1.0.0"
)

# Configuración de CORS
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://propequity.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir los Routers
app.include_router(auth.router) # El prefix /auth ya está definido en auth.py
app.include_router(simulator.router, prefix="/api/v1/simulator", tags=["Simulación"])

@app.get("/")
def read_root():
    return {
        "message": "Bienvenido a PropEquity API - Gestión Inmobiliaria",
        "docs": "/docs",
        "status": "Operational"
    }