from fastapi import FastAPI
from .database import engine, Base
from .api.v1 import simulator # Importar los demás cuando estén listos

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PropEquity API")

app.include_router(simulator.router, prefix="/api/v1/simulator", tags=["Simulación"])

@app.get("/")
def read_root():
    return {"message": "Bienvenido a PropEquity API - Gestión Inmobiliaria"}